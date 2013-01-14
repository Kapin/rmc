import datetime
import itertools

import mongoengine as me

import course as _course
import points as _points
import term as _term
import user_course as _user_course
import user_schedule_item as _user_schedule_item
from rmc.shared import constants
from rmc.shared import facebook
from rmc.shared import rmclogger
from rmc.shared import util

class User(me.Document):

    class JoinSource(object):
        FACEBOOK = 1

    meta = {
        'indexes': [
            'fb_access_token',
            'fbid',
        ],
    }

    # id = me.ObjectIdField(primary_key=True)

    # TODO(mack): join_date should be encapsulate in _id, but store it
    # for now, just in case; can remove it when sure that info is in _id
    join_date = me.DateTimeField(required=True)
    join_source = me.IntField(required=True, choices=[JoinSource.FACEBOOK])

    # eg. Mack
    first_name = me.StringField(required=True)

    middle_name = me.StringField()

    # eg. Duan
    last_name = me.StringField(required=True)

    # TODO(mack): check if facebook always returns gender field
    gender = me.StringField(choices=['male', 'female'])

    # eg. 1647810326
    fbid = me.StringField(required=True, unique=True)

    # http://stackoverflow.com/questions/4408945/what-is-the-length-of-the-access-token-in-facebook-oauth2
    fb_access_token = me.StringField(max_length=255, required=True, unique=True)
    fb_access_token_expiry_date = me.DateTimeField(required=True)
    # The token expired due to de-auth, logging out, etc (ie. not time expired)
    fb_access_token_invalid = me.BooleanField(default=False)

    email = me.EmailField()

    # eg. list of user objectids, could be friends from sources besides facebook
    friend_ids = me.ListField(me.ObjectIdField())
    # eg. list of fbids of friends from facebook, not necessarily all of whom
    # use the site
    friend_fbids = me.ListField(me.StringField())

    birth_date = me.DateTimeField( )

    last_visited = me.DateTimeField()
    # TODO(mack): consider using SequenceField()
    num_visits = me.IntField(min_value=0, default=0)

    # The last time the user visited the onboarding page
    last_show_onboarding = me.DateTimeField()
    # The last time the user was shown the import schedule view
    last_show_import_schedule = me.DateTimeField()

    # eg. mduan or 20345619 ?
    student_id = me.StringField()
    # eg. university_of_waterloo ?
    school_id = me.StringField()
    # eg. software_engineering ?
    # TODO(mack): should store program_id, not program_name
    # program_id = me.StringField()
    program_name = me.StringField()

    # List of UserCourse.id's
    course_history = me.ListField(me.ObjectIdField())

    # TODO(mack): figure out why last_term_id was commented out in
    # a prior diff: #260f174
    # Deprecated
    last_term_id = me.StringField()
    # Deprecated
    last_program_year_id = me.StringField()

    # Track the number of times the user has invited friends
    # (So we can award points if they have)
    num_invites = me.IntField(min_value=0, default=0)

    # The number of points this user has. Point are awarded for a number of
    # actions such as reviewing courses, inviting friends. This is a cached
    # point total. It will be calculated once a day with aggregator.py
    num_points = me.IntField(min_value=0, default=0)

    is_admin = me.BooleanField(default=False)

    # TODO(mack): refactor this into something maintainable
    sent_exam_schedule_notifier_email = me.BooleanField(default=False)
    sent_velocity_demo_notifier_email = me.BooleanField(default=False)
    sent_raffle_notifier_email = me.BooleanField(default=False)
    sent_raffle_end_notifier_email = me.BooleanField(default=False)
    sent_schedule_sharing_notifier_email = me.BooleanField(default=False)

    email_unsubscribed = me.BooleanField(default=False)

    # Note: Backfilled on night of Nov. 29th, 2012
    transcripts_imported = me.IntField(min_value=0, default=0)

    schedules_imported = me.IntField(min_value=0, default=0)

    last_bad_schedule_paste = me.StringField()
    last_good_schedule_paste = me.StringField()
    last_bad_schedule_paste_date = me.DateTimeField()
    last_good_schedule_paste_date = me.DateTimeField()

    # Whether this user imported a schedule when it was still broken and we
    # should email them to apologize
    schedule_sorry = me.BooleanField(default=False)

    @property
    def name(self):
        return '%s %s' % (self.first_name , self.last_name)

    def save(self, *args, **kwargs):

        # TODO(mack): If _changed_fields attribute does not exist, it mean
        # document has been saved yet. Just need to verify. In this case,
        # we could just check if id has been set
        first_save = not hasattr(self, '_changed_fields')

        if first_save:
            # TODO(Sandy): We're assuming people won't unfriend anyone.
            # Fix this later?

            # TODO(mack): this isn't safe against race condition of both
            # friends signing up at same time
            #print 'friend_fbids', self.friend_fbids
            friends = User.objects(fbid__in=self.friend_fbids).only('id', 'friend_ids')
            self.friend_ids = [f.id for f in friends]

        super(User, self).save(*args, **kwargs)

        if first_save:
            # TODO(mack): should do this asynchronously
            # Using update rather than save because it should be more efficient
            friends.update(add_to_set__friend_ids=self.id)

    # TODO(mack): think of better way to cache value
    @property
    def course_ids(self):
        if not hasattr(self, '_course_ids'):
            user_courses = _user_course.UserCourse.objects(
                id__in=self.course_history).only('course_id')
            self._course_ids = [uc.course_id for uc in user_courses]
        return self._course_ids

    @property
    # TODO(mack): support different sized pictures
    def fb_pic_url(self):
        return 'https://graph.facebook.com/%s/picture' % self.fbid

    @property
    def profile_url(self):
        return '/profile/%s' % self.id

    @property
    def absolute_profile_url(self):
        return '%s%s?admin=1' % (constants.PROD_HOST, self.profile_url)

    @property
    def short_program_name(self):
        if self.program_name:
            return self.program_name.split(',')[0]
        return ''

    @property
    def has_course_history(self):
        # TODO(Sandy): Using this to backfill transcripts imported, remove later
        if len(self.course_history) == 0:
            return False

        for uc in self.get_user_courses():
            if not _term.Term.is_shortlist_term(uc.term_id):
                return True
        return False

    @property
    def has_shortlisted(self):
        for uc in self.get_user_courses():
            if _term.Term.is_shortlist_term(uc.term_id):
                return True
        return False

    @property
    def has_schedule(self):
        # TODO(Sandy): Actually this only works assuming users never remove
        # their schedule and we'll have to do actual queries when 2013_05 comes
        return self.schedules_imported > 0

    @property
    def should_renew_fb_token(self):
        # Should renew FB token if it expired or will expire "soon".
        future_date = datetime.datetime.now() + datetime.timedelta(
                days=facebook.FB_FORCE_TOKEN_EXPIRATION_DAYS)
        return (self.fb_access_token_expiry_date < future_date or
                self.fb_access_token_invalid)

    @property
    def is_fb_token_expired(self):
        return (self.fb_access_token_expiry_date < datetime.datetime.now() or
                self.fb_access_token_invalid)

    @property
    def is_demo_account(self):
        return self.fbid == constants.DEMO_ACCOUNT_FBID

    def get_user_courses(self):
        return _user_course.UserCourse.objects(id__in=self.course_history)

    @classmethod
    def cls_mutual_courses_redis_key(cls, user_id_one, user_id_two):
        if user_id_one < user_id_two:
            first_id = user_id_one
            second_id = user_id_two
        else:
            first_id = user_id_two
            second_id = user_id_one
        return 'mutual_courses:%s:%s' %  (first_id, second_id)

    def mutual_courses_redis_key(self, other_user_id):
        return User.cls_mutual_courses_redis_key(self.id, other_user_id)

    def get_mutual_course_ids(self, redis):
        # fetch mutual friends from redis
        pipe = redis.pipeline()

        # Show mutual courses between the viewing user and the friends of the profile user
        for friend_id in self.friend_ids:
            pipe.smembers(self.mutual_courses_redis_key(friend_id))
        mutual_course_ids_per_user = pipe.execute()

        zipped = itertools.izip(
                self.friend_ids, mutual_course_ids_per_user)

        mutual_course_ids_by_friend = {}
        for friend_id, mutual_course_ids in zipped:
            mutual_course_ids_by_friend[friend_id] = mutual_course_ids

        return mutual_course_ids_by_friend

    def cache_mutual_course_ids(self, redis):
        friends = User.objects(id__in=self.friend_ids).only('course_history')
        friend_map = {}
        for friend in friends:
            friend_map[friend.id] = friend

        my_course_ids = set(self.course_ids)
        for friend in friends:
            mutual_course_ids = my_course_ids.intersection(friend.course_ids)
            if mutual_course_ids:
                redis_key = self.mutual_courses_redis_key(friend.id)
                redis.sadd(redis_key, *list(mutual_course_ids))

    def remove_mutual_course_ids(self, redis):
        pipe = redis.pipeline()

        for friend_id in self.friend_ids:
            pipe.delete(self.mutual_courses_redis_key(friend_id))

        return pipe.execute()

    def get_latest_program_year_id(self):
        latest_term_uc = None
        for uc_dict in self.get_user_courses():

            # Ignore untaken courses or shortlisted courses
            if uc_dict['term_id'] > util.get_current_term_id():
                continue

            if not latest_term_uc:
                latest_term_uc = uc_dict
            elif uc_dict['term_id'] > latest_term_uc['term_id']:
                latest_term_uc = uc_dict

        if latest_term_uc:
            return latest_term_uc['program_year_id']

        return None


    def to_dict(self, include_course_ids=False):
        program_name = self.short_program_name
        if include_course_ids:
            course_ids = self.course_ids
        else:
            course_ids = []

        return {
            'id': self.id,
            'fbid': self.fbid,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'name': self.name,
            'friend_ids': self.friend_ids,
            'fb_pic_url': self.fb_pic_url,
            'program_name': program_name,
            #'last_term_name': last_term_name,
            #'last_program_year_id': self.last_program_year_id,
            'course_history': self.course_history,
            'course_ids': course_ids,
            'num_invites': self.num_invites,
            'num_points': self.num_points,
        }

    # TODO(mack): make race condition safe?
    def delete(self, *args, **kwargs):
        # Remove this user from the friend lists of all friends
        friends = User.objects(id__in=self.friend_ids)
        friends.update(pull__friend_ids=self.id)

        # Delete all their user course objects
        _user_course.UserCourse.objects(user_id=self.id).delete()

        # TODO(mack): delete UserScheduleItems for this user

        # TODO(mack): delete mutual course information from redis?
        # should be fine for now since we are removing this user from their
        # friends' friend_ids, and redis cache will be regenerated daily
        # from aggregator.py

        return super(User, self).delete(*args, **kwargs)


    def to_review_author_dict(self, current_user, reveal_identity):
        is_current_user = current_user and current_user.id == self.id

        if reveal_identity:
            return {
                'id': self.id,
                'name': 'You' if is_current_user else self.name,
                'fb_pic_url': self.fb_pic_url,
            }

        else:
            return {
                'program_name': self.short_program_name
            }

    def invite_friend(self, redis):
        self.num_invites += 1
        if self.num_invites == 1:
            self.award_points(_points.PointSource.FIRST_INVITE, redis)

    def award_points(self, points, redis):
        self.num_points += points
        redis.incr('total_points', points)

    def update_fb_friends(self, fbids):
        self.friend_fbids = fbids
        fb_friends = User.objects(fbid__in=self.friend_fbids).only('id', 'friend_ids')
        # We only have friends from Facebook right now, so just set it
        self.friend_ids = [f.id for f in fb_friends]

    def get_schedule_item_dicts(self):
        schedule_item_objs = _user_schedule_item.UserScheduleItem.objects(
                user_id=self.id, term_id=util.get_current_term_id())
        return [si.to_dict() for si in schedule_item_objs]

    def add_course(self, course_id, term_id, program_year_id=None):
        '''
        Creates an UserCourse entry for the current user and adds it to the
        user's course_history

        Idempotent.
        '''
        user_course = _user_course.UserCourse.objects(
            user_id=self.id, course_id=course_id).first()

        if user_course is None:
            if _course.Course.objects.with_id(course_id) is None:
                # Non-existant course according to our data
                rmclogger.log_event(
                    rmclogger.LOG_CATEGORY_DATA_MODEL,
                    rmclogger.LOG_EVENT_UNKNOWN_COURSE_ID,
                    course_id
                )
                return

            user_course = _user_course.UserCourse(
                user_id=self.id,
                course_id=course_id,
                term_id=term_id,
                program_year_id=program_year_id,
            )
        else:
            # Record only the latest attempt for duplicate/failed courses
            if (term_id > user_course.term_id or
                user_course.term_id == _term.Term.SHORTLIST_TERM_ID):
                user_course.term_id = term_id
                user_course.program_year_id = program_year_id

        user_course.save()

        if user_course.id not in self.course_history:
            self.course_history.append(user_course.id)
            self.save()

    def __repr__(self):
        return "<User: %s>" % self.name
