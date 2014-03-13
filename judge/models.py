from django.contrib.auth.models import User
from django.db import models
from django.contrib import admin
import pytz

from operator import itemgetter


LANGUAGES = (
    ('PY', 'Python'),
    ('CPP', 'C++'),
)


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


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name='User associated')
    name = models.CharField(max_length=50, verbose_name='Display name', null=True, blank=True)
    about = models.TextField(verbose_name='Self-description', null=True, blank=True)
    timezone = models.CharField(max_length=50, verbose_name='Timezone', default='UTC', choices=TIMEZONE)
    language = models.CharField(max_length=50, verbose_name='Default language', choices=LANGUAGES, default='PY')

    def display_name(self):
        if self.name:
            return self.name
        return self.user.username

    def long_display_name(self):
        if self.name:
            return u'%s (%s)' % (self.user.username, self.name)
        return self.user.username

    def __unicode__(self):
        return u'Profile of %s in %s speaking %s' % (self.long_display_name(), self.timezone, self.language)


class ProfileAdmin(admin.ModelAdmin):
    fields = ['user', 'name', 'about', 'timezone', 'language']


class ProblemType(models.Model):
    name = models.CharField(max_length=20, verbose_name='Problem category ID')
    full_name = models.CharField(max_length=100, verbose_name='Problem category name')


class Problem(models.Model):
    name = models.CharField(max_length=100, verbose_name='Problem name')
    description = models.TextField(verbose_name='Problem body')
    user = models.ForeignKey(Profile, verbose_name='Creator')
    category = models.ManyToManyField(ProblemType, verbose_name='Type of problem')
    time_limit = models.FloatField(verbose_name='Time limit for execution')
    memory_limit = models.FloatField(verbose_name='Memory limit')
    points = models.FloatField(verbose_name='Points this problem is worth')
    partial = models.BooleanField(verbose_name='Whether partial points are allowed')


class Comment(models.Model):
    user = models.ForeignKey(Profile, verbose_name='User who posted this comment')
    problem = models.ForeignKey(Problem, null=True, verbose_name='Problem this comment is associated with')
    title = models.CharField(max_length=200, verbose_name='Title of comment')
    body = models.TextField(verbose_name='Body of comment')


class Submission(models.Model):
    user = models.ForeignKey(Profile)
    problem = models.ForeignKey(Problem)
    time = models.FloatField(verbose_name='Execution time', null=True)
    memory = models.FloatField(verbose_name='Memory usage', null=True)
    points = models.FloatField(verbose_name='Points granted', null=True)

admin.site.register(Profile, ProfileAdmin)
