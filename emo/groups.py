from core_app.models import LateremGroupMembership, LateremGroup, LateremUser, LateremWork, LateremAssignment
from extratypes import DBHybrid
from .works import Work

class Member(DBHybrid):
    def __init__(self, dbobj, group):
        super().__init__(dbobj)
        self.group = group
        self.dbmembership = LateremGroupMembership.objects.get(user=dbobj,
                                                               group=group.dbmodel)
    
    def get_permission(self, permission):
        if self.dbmembership.is_group_admin:
            return True
        elif permission.startswith('can'):
            return self.dbmembership.__getattribute__(permission)
        else:
            return False

class Group(DBHybrid):
    def get_members(self):
        return [Member(x, self) for x in LateremUser.objects.filter(lateremgroupmembership__group=self.dbmodel)]
    
    def get_works(self):
        return [Work(x) for x in LateremWork.objects.filter(lateremassignment__group=self.dbmodel)]
    

    