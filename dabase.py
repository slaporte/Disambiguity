import peewee as pw
from datetime import datetime

dab_db = pw.SqliteDatabase(None) #deferred initialization

def init(db_name, **kwargs):
    dab_db.init(str(db_name)+'.db', **kwargs)
    dab_db.connect()
    Dabblet.create_table(fail_silently=True)
    DabChoice.create_table(fail_silently=True)


class DabModel(pw.Model):
    class Meta:
        database = dab_db


class Dabblet(DabModel):
    title   = pw.CharField()
    context = pw.TextField()

    source_title  = pw.CharField()
    source_order  = pw.IntegerField()
    source_pageid = pw.IntegerField()
    source_revid  = pw.IntegerField()
    source_images = pw.TextField() # refactor to another table

    date_created  = pw.DateTimeField(db_index=True)

    difficulty    = pw.IntegerField()
    viability     = pw.IntegerField()
    
    @classmethod
    def from_page(cls, title, context, source_page, source_order, 
                  source_images, **kw):
        # TODO: get options
        ret = cls(title = title,
                  context = context,
                  source_title = source_page.title,
                  source_pageid = source_page.pageid,
                  source_revid = source_page.revisionid,
                  source_order = source_order,
                  source_images = source_images,
                  date_created = datetime.now())
                  
        ret.source_page = source_page
        return ret

    def _asdict(self):
        return {'title': self.title,
                'source_title': self.source_title,
                'context': self.context,
                'images': self.source_images,
                'options': [ o._asdict() for o in self.options ]
                }


class DabChoice(DabModel):
    dabblet = pw.ForeignKeyField(Dabblet, related_name='choices')
    title   = pw.CharField()
    text    = pw.TextField()

    def _asdict(self):
        return { 'title':     self.title,
                 'text':      self.text,
                 'dab_title': self.dabblet.title }


class DabbletSolution(DabModel):
    dabblet = pw.ForeignKeyField(Dabblet, related_name='dabblet')
    choice  = pw.ForeignKeyField(DabChoice, related_name='choice')
    
    solver_ip   = pw.CharField()
    date_solved = pw.DateTimeField(db_index=True)


def test():
    from datetime import datetime
    from dabnabbit import Page

    init('dabase_unittest')
    sp = Page(0, 'first_source', 0, 'first text', True, datetime.now())
    
    #da2 = Dabblet(title='first', context='first context', source_title='first source', source_pageid=0, source_revid=0, source_order=0, date_created=datetime.now())
    da2 = Dabblet.from_page('first dab title', 'first dab context', sp, 0)
    da2.save()

    dabblets = [ d for d in Dabblet.select() ]
    print len(dabblets), 'Dabblets now in the test db'


if __name__ == '__main__':
    test()
