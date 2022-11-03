import json
from context_objects import SPACE_REPLACER, WORK_DIR
from .forms import *
from dtm.works import Work

def count_work(taskname):
    return taskname[taskname.rfind('/') + 1 : taskname[taskname.rfind('/') + 1 : ].find('_id')]

def fill_additional_args(request, taskname, theme):
    work_name, taskid = taskname.split('_id')
    taskid = taskid.replace(SPACE_REPLACER, ' ')
    work_path = Work.split_full_name(work_name, separator='.', space_replacement=SPACE_REPLACER)
    workobject = Work(work_path)

    ret = {}
    work_name = count_work(taskname)
    ret['button1'] = AddAnswerForm()
    ret['workdir'] = WORK_DIR
    ret['meta_tasktype'] = workobject.tasks[taskid]
    ret['task_list'] = workobject.tasks.keys()
    ret['task_name'] = taskid
    ret['work_name'] = work_path[-1]
    ret['user'] = request.user
    if not theme:
        theme = 'dark'
    ret['theme'] = theme
    return ret

def change_color_theme(request):
    if 'color-theme' not in request.session:
        request.session['color-theme'] = 'dark'
    
    if request.session['color-theme'] == 'dark':
        request.session['color-theme'] = 'light'
    elif request.session['color-theme'] == 'light':
        request.session['color-theme'] = 'dark'