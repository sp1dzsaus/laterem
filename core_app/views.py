from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import PermissionDenied
from context_objects import LTM_SCANNER
from os.path import join as pathjoin
from os import mkdir
from .views_functions import render_args, change_color_theme, DEBUG_assure_admin
from .models import *
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, NewUser, AddMember, AssignWork, UploadTask

from dbapi.users import User
from dbapi.tasks import Task, CompiledTask, Work, Category
from dbapi.solutions import Verdicts
from dbapi.groups import Group

def permission_required(permission):
    def wrapper(function):
        def wrap(request, *args, **kwargs):
            if not User(request.user).has_global_permission(permission):
                raise PermissionDenied()
            return function(request, *args, **kwargs)
        return login_required(wrap)
    return wrapper

def every_permission_required(*permissions):
    def wrapper(function):
        def wrap(request, *args, **kwargs):
            for permission in permissions:
                if not User(request.user).has_global_permission(permission):
                    raise PermissionDenied()
            return function(request, *args, **kwargs)
        return login_required(wrap)
    return wrapper

def any_permission_required(*permissions):
    def wrapper(function):
        def wrap(request, *args, **kwargs):
            for permission in permissions:
                if User(request.user).has_global_permission(permission):
                    return function(request, *args, **kwargs)
            raise PermissionDenied()
        return login_required(wrap)
    return wrapper

def logout_view(request):
    logout(request)
    return redirect('/')

def login_view(request):
    # <Костыль>
    DEBUG_assure_admin()
    # </Костыль>
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next'))
        else:
            return HttpResponse('<h1>Такого аккаунта не существует! или данные некорректные</h1>')
    else:
        form = LoginForm()
        return render(request, 'login.html', render_args(additional={'form': form}))

@login_required
def profile_view(request):
    if request.method == 'POST':  
        # Обработка кнопки смены темы
        if 'change-color-theme' in request.POST:
            with User(request.user) as user:
                change_color_theme(user, request)
                return redirect(request.path)
    with User(request.user) as user:
        return render(request, 'profile_page.html', render_args(me=user, 
                                                                additional={'title': 'Laterem Настройки', 
                                                                'workdir': dict()})) # <- Костыыыль! 

@any_permission_required("can_manage_users", "can_manage_works", "can_manage_groups", "can_manage_tasks")
def teacher_hub(request):
    return render(request, "teacher_panel/teacher_panel_base.html", render_args())

@permission_required("can_manage_users")
def users_panel(request):
    if request.method == 'POST':
        if "newuser" in request.POST:
            form = NewUser(request.POST)
            if form.is_valid():
                test = LateremUser.objects.filter(email=form.cleaned_data['email'])
                if test:
                    # Пользователь с такой почтой уже есть, надо как-то оповестить 
                    pass
                else:
                    LateremUser.objects.create_user(email=form.cleaned_data['email'], password=form.cleaned_data['password'],
                                                    username=form.cleaned_data['email'], first_name=form.cleaned_data['first_name'],
                                                    last_name=form.cleaned_data['second_name'],
                                                    settings="{}")

        else:
    # <Плохо! Переписать>
            flag = False
            for signal in request.POST:
                if signal.startswith('delete:'):
                    email = signal[len('delete:'):]
                    user = LateremUser.objects.get(email=email)
                    user.delete()
                    flag = True
                    break
                elif signal.startswith('edit:'):
                    email = signal.lstrip('edit:')
                    user = LateremUser.objects.get(email=email)
                    user.email = request.POST.get('user_email')
                    #if request.POST.get('user_password'):
                     #   user.password = request.POST.get('user_password')
                    user.first_name = request.POST.get('user_name')
                    user.last_name = request.POST.get('user_lastname')
                    user.save()
    form = NewUser()
    return render(request, "teacher_panel/user_panel.html", render_args(meta_all_users_available=True,
                                                                        additional={'newuserform': form}))

@permission_required("can_manage_works")
def work_panel(request):
    if request.method == 'POST':
        for signal in request.POST:
            if signal.startswith('add-work-'):
                cat_id = signal[len('add-work-'):]
                if cat_id == 'mother':
                    with Work(LateremWork.objects.create(name="Новая работа",
                                                         author=request.user,
                                                        )) as new:
                        return redirect('/teacher/works/' + str(new.id))
                else:
                    # /!\ Typecast warning
                    cat = Category.by_id(int(cat_id))
                    with Work(LateremWork.objects.create(name="Новая работа",
                                                         author=request.user,
                                                         category=cat.dbmodel
                                                        )) as new:
                        return redirect('/teacher/works/' + str(new.id))
            elif signal.startswith('add-category-'):
                cat_id = signal[len('add-category-'):]
                if cat_id == 'mother':
                    with Category(LateremCategory.objects.create(name="Новая категория",
                                                                         )) as new:
                        return redirect(request.path)
                else:
                    # /!\ Typecast warning
                    cat = int(cat_id)
                    with Category(LateremCategory.objects.create(name="Новая категория",
                                                                         root_category=cat
                                                                         )) as new:
                        return redirect(request.path)
            elif signal.startswith('edit-'):
                s_cat_id = signal[len('edit-'):]
                # /!\ Typecast warning
                cat_id = int(s_cat_id)
                with Category.by_id(cat_id) as cat:
                    cat.dbmodel.name = request.POST.get('input-' + s_cat_id, 'Empty')
                    cat.dbmodel.save()
                    return redirect(request.path)
    
    return render(request, "teacher_panel/work_panel/work_panel.html", render_args(meta_all_works_available=True,
                                                                        me=User(request.user),
                                                                        ))

@permission_required("can_manage_works")
def manage_work(request, work_id):
    work = Work.by_id(work_id)

    if request.method == 'POST':
        for signal in request.POST:
            if signal.startswith('delete:'):
                id = int(signal.lstrip('delete:'))
                task = Task.by_id(id)
                work.remove_task(task)
                return redirect(request.path)
        if 'edit_data' in request.POST:
            name = request.POST.get('work_name')
            work.dbmodel.name = name
            work.dbmodel.save()
            return redirect(request.path)
        if 'newtask' in request.POST:
            task = work.add_task(name=request.POST.get('task_name'), 
                                 task_type=request.POST.get('task_type'))
            return redirect(request.path)
        if 'appoint_to_group' in request.POST:
            group = Group.by_id(request.POST.get('group_name'))
            group.assign(work, User(request.user))
            return redirect(request.path)
    groups_to_appoint = list()
    for group in User(request.user).groups():
        if not work in group.get_works():
            groups_to_appoint.append((group.id, group.name))
    return render(request, 'teacher_panel/work_panel/work_manage.html', render_args(meta_all_task_types_available=True,
                                                                         me=User(request.user),
                                                                         additional={'work': work,
                                                                         'groups_to_appoint': groups_to_appoint}))



@permission_required("can_manage_groups")
def group_panel(request):
    if request.method == 'POST':
        if 'new-group' in request.POST:
            with Group(LateremGroup.objects.create(name="Новая группа")) as new:
                new.add_member(User(request.user), is_group_admin=True)
                return redirect('/teacher/groups/' + str(new.id))
    return render(request, "teacher_panel/group_panel/group_panel.html", render_args(meta_all_groups_available=True,
                                                                          ))

@permission_required("can_manage_groups")
def manage_group(request, group_id):
    group = Group.by_id(group_id)
    me = User(request.user)

    if request.method == 'POST':
        if 'delete_group' in request.POST:
            group.dbmodel.delete()
            return redirect('/teacher/groups/')

        if 'edit_data' in request.POST:
            name = request.POST.get('group_name', 'Empty')
            description = request.POST.get('group_description')
            group.dbmodel.name = name
            group.dbmodel.description = description
            group.dbmodel.save()
            return redirect(request.path)

        for signal in request.POST:
            if signal.startswith('delete:'):
                email = signal[len('delete:'):]
                user = User.get(email=email)
                group.remove_member(user)
                return redirect(request.path)
        assign_work_form = AssignWork(request.POST)
        if assign_work_form.is_valid():
            work = Work.by_id(assign_work_form.cleaned_data['id'])
            group.assign(work, me)
            return redirect(request.path)
        if 'newuser' in request.POST:
            user = User.get(email=request.POST.get('user_email'))
            group.add_member(user)
            return redirect(request.path)
    else:
        assign_work_form=AssignWork()
        

    users = list()

    for user in map(User, LateremUser.objects.all()):
        if user not in group.get_members():
            users.append(user)

    return render(request, 'teacher_panel/group_panel/group_manage.html', render_args(current_group=group,
                                                                          additional={"assign_work_form": assign_work_form,
                                                                                      "users": users,
                                                                                      }))

@permission_required("can_manage_tasks")
def task_panel(request):
    if request.method == "POST":
        if 'newtask' in request.POST:
            name = request.POST.get('task_type_name')
            path = pathjoin('data', 'tasks', name)
            mkdir(path)
            config = request.FILES.get('config_file')
            view = request.FILES.get('view_file')
            print('POST:', request.POST, '; FILES:', request.FILES)
            with open(pathjoin(path, 'config.ltc'), 'wb+') as dest:
                for chunk in config.chunks():
                    dest.write(chunk)
            with open(pathjoin(path, 'view.html'), 'wb+') as dest:
                for chunk in view.chunks():
                    dest.write(chunk)
        return redirect(request.path)
    # Временное решение
    # try:
    return render(request, 'teacher_panel/task_panel/task_panel.html', render_args(additional={"all_templates": LTM_SCANNER.all_shoots()}))
    # except NotADirectoryError:
    #     print('! ERROR !\tДирректория data/tasks пуста. Нет доступных шаблонов')
    #     return render(request, 'teacher_panel/task_panel/task_panel.html', render_args(additional={"all_templates": ""}))

# Рендер страницы работы
@login_required
def render_work(request, work_id):
    work_id = int(work_id)

    work = Work.by_id(work_id)
    #if 'compiled_tasks' in request.session: 
     #   request.session.modified = True
      #  request.session['compiled_tasks'] = {}
    return redirect('/task/' + str(work.tasks()[0].id))


def getasset(request, taskname, filename):
    if filename == 'view.html' or filename == 'config.ltc':
        raise PermissionDenied()
    path = LTM_SCANNER.id_to_path(taskname)
    path = pathjoin(path, filename)
    return FileResponse(open(path, 'rb'))

# Функция рендера (обработки и конечного представления на сайте) задачи по имени (имя берётся из адресной строки)
@login_required
def task_view(request, stask_id):
    if 'compiled_tasks' not in request.session: 
        request.session['compiled_tasks'] = {}

    task_id = int(stask_id)
    task = Task.by_id(task_id)
    if stask_id not in request.session['compiled_tasks']:
        compiled_task = task.compile()
        request.session['compiled_tasks'][stask_id] = compiled_task.as_JSON()
        request.session.modified = True
    else:
        compiled_task = CompiledTask.from_JSON(request.session['compiled_tasks'][stask_id])

    if request.method == 'POST':
        # Проверка - есть ли нажатая нами кнопка в списке задач (нужно для переадрессации на другие задачи)
        for el in request.POST:
            if el.startswith('redirect:task'):
                # Переадрессация на задачу
                l_task_id = el.lstrip('redirect:task')
                return redirect('/task/' + l_task_id)

        # Анализ ответа
        if compiled_task.test(dict(request.POST)):
            with User(request.user) as user:
                user.solve(task, compiled_task.ltc.mask_answer_dict(dict(request.POST)), Verdicts.OK)
            return redirect(request.path)
        with User(request.user) as user:
            user.solve(task, dict(request.POST), Verdicts.WRONG_ANSWER)
        return redirect(request.path)
    return render(request, "work_base.html", render_args(me=User(request.user),
                                                         current_task=task,
                                                         additional=compiled_task.ltc.field_table))

# Базовая страница сайта
@login_required
def student_page_render(request):
    with User(request.user) as user:
        if not request.session.get('color-theme'):
            request.session['color-theme'] = user.get_setting('theme')
        return render(request, 'student.html', render_args(me=User(request.user),
                                                         additional={'title': 'Laterem',
                                                                     'text': 'Это базовая страница',
                                                                     'text2': 'Перейдите на нужную работу по ссылке слева'}))

def main_page_render(request):
    with User(request.user) as user:
        return render(request,
                    'main.html',
                    {
                        'title': 'Laterem'
                    }
                    )
