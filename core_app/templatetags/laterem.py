from django import template
from django.utils.safestring import SafeString
from ltm.tasks import Verdicts
from ltm.users import User
from ltm.works import Work
from context_objects import SEPARATOR

register = template.Library()

@register.simple_tag(takes_context=True)
def asset(context, format_string):
    taskname = context['meta_tasktype']
    path = '/taskasset' + '/' + taskname + '/' + format_string
    return path


# Кол-во вызовов = кол-во ключей во всех слоях mask
def mask_tree(source, mask):
    if not mask:
        return source
    output = {}
    for key, value in source.items():
        if key in mask:
            output[key] = mask_tree(value, mask[key])
    return output

def draw_progress_line(args):
    ret = '<table class="progress_line" cellpadding="0px"><tr>'
    for verdict, l in args:
        if l > 0:
            ret += '<td class="' + verdict + '" height="4px" width=' + str(l * 100).replace('.', ',')  + '%></td>'
    ret += '</tr></table>'
    return ret

# Кол-во вызовов = кол-во словарей в mask_tree(WORK_DIR, user.raw_available_branches)
def _submenu(inp, user: User, path=[], outer=False):
    if outer:
        output = '<ul id="myUL">'
    else:
        output = '<ul class="nested">'
    
    for key, value in inp.items():
        if isinstance(value, dict):
            output += '<li><span class="caret">' + key + '</span>' + _submenu(value, user, path=path + [key]) + '</li>'
        else:
            output += '<li><span class="caret">' + key + '</span><ul class="nested">'
            for work in value:
                element = work[work.find(SEPARATOR, work.find(SEPARATOR) + 1) + 1:work.rfind('.')]
                name = element[element.rfind(SEPARATOR) + 1:]
                addr = element.replace(SEPARATOR, '.')
                stats = user.get_work_stats(path + [key] + [name], True)
                verdict = Work.stat_to_average_verdict(stats)
                line_len = 0 # Придумай циферку жура 
                # Ниже - значения от 0 до 1, обозначающие пропорции. 
                # Для получения длины сегмента линии конкретного цвета достаточно
                # Домножить штуки ниже на line_len
                green_len = stats[Verdicts.OK]
                orange_len = stats[Verdicts.SENT] + stats[Verdicts.PARTIALLY_SOLVED]
                red_len = stats[Verdicts.WRONG_ANSWER]
                gray_len = stats[Verdicts.NO_ANSWER]


                line_args = [("correct", green_len), ("unchecked", orange_len), ("wrong", red_len), ("no-answer", gray_len)]

                if verdict == Verdicts.NO_ANSWER:
                    output += '<li><a href="' + 'http://localhost:8000/works/' + addr + '">' + name + '</a>' + draw_progress_line(line_args) + '</li>'
                else:
                    # Оперделение состояния задания
                    if verdict == Verdicts.OK:
                        output += '<li><a href="' + 'http://localhost:8000/works/' + addr + '">' + name + '</a>' + draw_progress_line(line_args) + '</li>'
                    elif verdict == Verdicts.WRONG_ANSWER:
                        output += '<li><a href="' + 'http://localhost:8000/works/' + addr + '">' + name + '</a>' + draw_progress_line(line_args) + '</li>'
                    else:
                        output += '<li><a href="' + 'http://localhost:8000/works/' + addr + '">' + name + '</a>'+ draw_progress_line(line_args) + '</li>'
            output += '</ul></li>'

    output += '</ul>'
    return output

@register.simple_tag(takes_context=True)
def tree(context, treename):
    try:
        user = context['user']
        rtree = mask_tree(context[treename], user.raw_available_branches) 
        return SafeString(_submenu(rtree, user, outer=True))
    except KeyError:
        return ''
