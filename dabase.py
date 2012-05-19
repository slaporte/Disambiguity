import peewee as pw
from datetime import datetime

dab_db = pw.SqliteDatabase(None) #deferred initialization

def init(db_name='dabase', **kwargs):
    dab_db.init(str(db_name)+'.db', **kwargs)
    dab_db.connect()
    Dabblet.create_table(fail_silently=True)
    DabChoice.create_table(fail_silently=True)
    DabImage.create_table(fail_silently=True)
    DabSolution.create_table(fail_silently=True)

class DabModel(pw.Model):
    class Meta:
        database = dab_db


class Dabblet(DabModel):
    CONTEXT_THRESHOLD = 250
    CHOICES_THRESHOLD = 12
    
    title   = pw.CharField()
    context = pw.TextField()

    source_title  = pw.CharField()
    source_order  = pw.IntegerField()
    source_pageid = pw.IntegerField()
    source_revid  = pw.IntegerField()

    date_created  = pw.DateTimeField(db_index=True)

    difficulty    = pw.IntegerField()
    priority      = pw.IntegerField()
    
    @classmethod
    def from_page(cls, title, context, source_page, source_order, 
                  source_imgs, **kw):
        # TODO: get options
        ret = cls(title = title,
                  context = context,
                  source_title = source_page.title,
                  source_pageid = source_page.pageid,
                  source_revid = source_page.revisionid,
                  source_order = source_order,
                  date_created = datetime.now())
                  
        ret.source_page = source_page
        ret.source_imgs = source_imgs
        return ret

    def get_priority(self):
        priority = 5
        choice_count = self.choices.count()
        
        if choice_count > 0:
            priority -= 1
            if choice_count < self.CHOICES_THRESHOLD:
                priority -= 1
            
            if len(self.context.split()) < self.CONTEXT_THRESHOLD:
                priority -= 1
                
            if self.images.count() > 0:
                priority -= 1
            
        return priority
    
    @property
    def jsondict(self):
        return {
            'id': self.id,
            'title': self.title,
            'source_title': self.source_title,
            'source_order': self.source_order,
            'context': self.context,
            'images':  [ i.src for i in self.images],
            'choices': [ c.jsondict for c in self.choices ],
            'priority': self.priority,
            'difficulty': self.difficulty
            }


class DabChoice(DabModel):
    dabblet = pw.ForeignKeyField(Dabblet, related_name='choices')
    title   = pw.CharField()
    text    = pw.TextField()
    
    @property
    def jsondict(self):
        return { 'dabblet_id': self.dabblet.id,
                 'choice_id': self.id,
                 'title':     self.title,
                 'text':      self.text,
                 'dab_title': self.dabblet.title }
    

class DabImage(DabModel):
    dabblet = pw.ForeignKeyField(Dabblet, related_name='images')
    src     = pw.TextField()


class DabSolution(DabModel):
    dabblet = pw.ForeignKeyField(Dabblet, related_name='dabblet')
    choice  = pw.ForeignKeyField(DabChoice, null=True, related_name='choice')
    
    solver_ip    = pw.CharField()
    solver_index = pw.IntegerField()
    date_solved  = pw.DateTimeField(db_index=True)

    @property
    def jsondict(self):
        return { 'dabblet_id':  self.dabblet.id,
                 'choice_id':   self.choice and self.choice.id,
                 'solver_ip':   self.title,
                 'solver_index':self.solver_index,
                 'date':        str(self.date_solved) }


def test():
    from datetime import datetime
    from dabnabbit import Page

    init('dabase_unittest')
    sp = Page('first_source', 'first_source', 0, 0, 'first text', True, datetime.now())
    
    #da2 = Dabblet(title='first', context='first context', source_title='first source', source_pageid=0, source_revid=0, source_order=0, date_created=datetime.now())
    da2 = Dabblet.from_page('first dab title', 'first dab context', sp, 0, '')
    da2.save()

    dabblets = [ d for d in Dabblet.select() ]
    print len(dabblets), 'Dabblets now in the test db'


if __name__ == '__main__':
    test()
