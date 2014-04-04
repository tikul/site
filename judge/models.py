from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max
import pytz
from operator import itemgetter, attrgetter

from judge.judgeapi import judge_submission, abort_submission


def make_timezones():
    data = {}
    for tz in pytz.all_timezones:
        if '/' in tz:
            area, loc = tz.split('/', 1)
        else:
            area, loc = 'Other', tz
        if area in data:
            data[area].append((tz, loc))
        else:
            data[area] = [(tz, loc)]
    data = data.items()
    data.sort(key=itemgetter(0))
    return data


TIMEZONE = make_timezones()
del make_timezones


if 'tinymce' in settings.INSTALLED_APPS:
    from tinymce.models import HTMLField
else:
    HTMLField = models.TextField


class Language(models.Model):
    key = models.CharField(max_length=6, verbose_name='Short identifier', unique=True)
    name = models.CharField(max_length=20, verbose_name='Name as shown to user')

    def __unicode__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name='User associated')
    name = models.CharField(max_length=50, verbose_name='Display name', null=True, blank=True)
    about = models.TextField(verbose_name='Self-description', null=True, blank=True)
    timezone = models.CharField(max_length=50, verbose_name='Timezone', default='UTC', choices=TIMEZONE)
    language = models.ForeignKey(Language, verbose_name='Default language')
    points = models.FloatField(default=0, db_index=True)

    def calculate_points(self):
        self.points = sum(map(itemgetter('points'),
                              Submission.objects.filter(user=self).values('problem_id').distinct()
                                        .annotate(points=Max('points'))))
        self.save()
        return self.points

    def display_name(self):
        if self.name:
            return self.name
        return self.user.username

    def long_display_name(self):
        if self.name:
            return u'%s (%s)' % (self.user.username, self.name)
        return self.user.username

    def is_admin(self):
        return self.user.is_superuser or self.user.groups.filter(name='Admin').exists()

    @property
    def problems(self):
        return Submission.objects.filter(user=self, points__gt=0).values('problem').distinct().count()

    def __unicode__(self):
        #return u'Profile of %s in %s speaking %s' % (self.long_display_name(), self.timezone, self.language)
        return self.long_display_name()


class ProblemType(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem category ID', unique=True)
    full_name = models.CharField(max_length=100, verbose_name='Problem category name')

    def __unicode__(self):
        return self.full_name


class ProblemGroup(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem group ID', unique=True)
    full_name = models.CharField(max_length=100, verbose_name='Problem group name')

    def __unicode__(self):
        return self.full_name


class Problem(models.Model):
    code = models.CharField(max_length=20, verbose_name='Problem code', unique=True)
    name = models.CharField(max_length=100, verbose_name='Problem name', db_index=True)
    description = HTMLField(verbose_name='Problem body')
    user = models.ForeignKey(Profile, verbose_name='Creator')
    types = models.ManyToManyField(ProblemType, verbose_name='Problem types')
    groups = models.ManyToManyField(ProblemGroup, verbose_name='Problem groups')
    time_limit = models.FloatField(verbose_name='Time limit')
    memory_limit = models.FloatField(verbose_name='Memory limit')
    points = models.FloatField(verbose_name='Points')
    partial = models.BooleanField(verbose_name='Allows partial points')
    allowed_languages = models.ManyToManyField(Language, verbose_name='Allowed languages')

    def types_list(self):
        return map(attrgetter('full_name'), self.types.all())

    def languages_list(self):
        return map(attrgetter('name'), self.allowed_languages.all())

    def number_of_users(self):
        return Submission.objects.filter(problem__code=self.code).values('user').distinct().count()

    def __unicode__(self):
        return self.name


class Comment(models.Model):
    user = models.ForeignKey(Profile, verbose_name='User who posted this comment')
    time = models.DateTimeField(verbose_name='Comment time')
    problem = models.ForeignKey(Problem, null=True, verbose_name='Associated problem')
    title = models.CharField(max_length=200, verbose_name='Title of comment')
    body = models.TextField(verbose_name='Body of comment')


SUBMISSION_RESULT = (
    ('AC', 'Accepted'),
    ('WA', 'Wrong Answer'),
    ('TLE', 'Time Limit Exceeded'),
    ('MLE', 'Memory Limit Exceeded'),
    ('IR', 'Invalid Return'),
    ('RTE', 'Runtime Error'),
    ('CE', 'Compile Error'),
    ('IE', 'Internal Error'),
)


class Submission(models.Model):
    STATUS = (
        ('QU', 'Queued'),
        ('C', 'Compiled'),
        ('G', 'Grading'),
        ('D', 'Completed'),
        ('IE', 'Internal Error'),
        ('CE', 'Compile Error'),
    )

    user = models.ForeignKey(Profile)
    problem = models.ForeignKey(Problem)
    date = models.DateTimeField(verbose_name='Submission time', auto_now_add=True)
    time = models.FloatField(verbose_name='Execution time', null=True, db_index=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True, db_index=True)
    language = models.ForeignKey(Language, verbose_name='Submission language')
    source = models.TextField(verbose_name='Source code')
    status = models.CharField(max_length=2, choices=STATUS, default='QU', db_index=True)
    result = models.CharField(max_length=3, choices=SUBMISSION_RESULT, default=None, null=True,
                              blank=True, db_index=True)

    def judge(self):
        return judge_submission(self)

    def abort(self):
        return abort_submission(self)

    def is_graded(self):
        return self.status not in ["QU", "C", "G"]

    def __unicode__(self):
        return u'Submission %d of %s by %s' % (self.id, self.problem, self.user)

    class Meta:
        permissions = (
            ('rejudge_submission', 'Rejudge the submission'),
            ('rejudge_submission_lot', 'Rejudge a lot of submissions'),
            ('spam_submission', 'Submit without limit')
        )


class SubmissionTestCase(models.Model):
    submission = models.ForeignKey(Submission, verbose_name='Associated submission')
    case = models.IntegerField(verbose_name='Test case ID')
    status = models.CharField(max_length=3, verbose_name='Status flag', choices=SUBMISSION_RESULT)
    time = models.FloatField(verbose_name='Execution time', null=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True)
    total = models.FloatField(verbose_name='Points possible', null=True)

