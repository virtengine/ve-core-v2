from __future__ import unicode_literals

import re
import warnings

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, UserManager, SiteProfileNotAvailable)
from django.core import validators
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import send_mail
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition
from rest_framework.authtoken.models import Token
from uuidfield import UUIDField


class DescribableMixin(models.Model):
    """
    Mixin to add a standardized "description" field.
    """
    class Meta(object):
        abstract = True

    description = models.CharField(_('description'), max_length=500, blank=True, null=True)


class UiDescribableMixin(DescribableMixin):
    """
    Mixin to add a standardized "description" and "icon url" fields.
    """
    class Meta(object):
        abstract = True

    icon_url = models.URLField(_('icon url'), null=True, blank=True)


class UuidMixin(models.Model):
    """
    Mixin to identify models by UUID.
    """
    class Meta(object):
        abstract = True

    uuid = UUIDField(auto=True, unique=True)


class User(UuidMixin, DescribableMixin, AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        _('username'), max_length=30, unique=True,
        help_text=_('Required. 30 characters or fewer. Letters, numbers and '
                    '@/./+/-/_ characters'),
        validators=[
            validators.RegexValidator(re.compile('^[\w.@+-]+$'), _('Enter a valid username.'), 'invalid')
        ])
    civil_number = models.CharField(_('civil number'), max_length=10, unique=True, blank=True, null=True, default=None)
    full_name = models.CharField(_('full name'), max_length=100, blank=True)
    native_name = models.CharField(_('native name'), max_length=100, blank=True)
    phone_number = models.CharField(_('phone number'), max_length=40, blank=True)
    organization = models.CharField(_('organization'), max_length=80, blank=True)
    job_title = models.CharField(_('job title'), max_length=40, blank=True)
    email = models.EmailField(_('email address'), blank=True)

    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user can log into this admin '
                                               'site.'))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this user should be treated as '
                                                'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta(object):
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def email_user(self, subject, message, from_email=None):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email])

    def get_profile(self):
        """
        Returns site-specific profile for this user. Raises
        SiteProfileNotAvailable if this site does not allow profiles.
        """
        warnings.warn("The use of AUTH_PROFILE_MODULE to define user profiles has been deprecated.",
                      DeprecationWarning, stacklevel=2)
        if not hasattr(self, '_profile_cache'):
            from django.conf import settings
            if not getattr(settings, 'AUTH_PROFILE_MODULE', False):
                raise SiteProfileNotAvailable(
                    'You need to set AUTH_PROFILE_MODULE in your project '
                    'settings')
            try:
                app_label, model_name = settings.AUTH_PROFILE_MODULE.split('.')
            except ValueError:
                raise SiteProfileNotAvailable(
                    'app_label and model_name should be separated by a dot in '
                    'the AUTH_PROFILE_MODULE setting')
            try:
                model = models.get_model(app_label, model_name)
                if model is None:
                    raise SiteProfileNotAvailable(
                        'Unable to load the profile model, check '
                        'AUTH_PROFILE_MODULE in your project settings')
                self._profile_cache = model._default_manager.using(
                    self._state.db).get(user__id__exact=self.id)
                self._profile_cache.user = self
            except (ImportError, ImproperlyConfigured):
                raise SiteProfileNotAvailable
        return self._profile_cache


def validate_ssh_public_key(ssh_key):
    # http://stackoverflow.com/a/2494645
    import base64
    import struct

    try:
        key_parts = ssh_key.split(' ', 2)
        key_type, key_body = key_parts[0], key_parts[1]

        if key_type != 'ssh-rsa':
            raise ValidationError('Invalid SSH public key type %s, only ssh-rsa is supported' % key_type)

        data = base64.decodestring(key_body)
        int_len = 4
        # Unpack the first 4 bytes of the decoded key body
        str_len = struct.unpack('>I', data[:int_len])[0]

        encoded_key_type = data[int_len:int_len + str_len]
        # Check if the encoded key type equals to the decoded key type
        if encoded_key_type != key_type:
            raise ValidationError("Invalid encoded SSH public key type %s within the key's body, "
                                  "only ssh-rsa is supported" % encoded_key_type)
    except IndexError:
        raise ValidationError('Invalid SSH public key structure')

    except (base64.binascii.Error, struct.error):
        raise ValidationError('Invalid SSH public key body')


@python_2_unicode_compatible
class SshPublicKey(UuidMixin, models.Model):
    """
    User public key.

    Used for injection into VMs for remote access.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True)
    name = models.CharField(max_length=50, blank=True)
    fingerprint = models.CharField(max_length=47)  # In ideal world should be unique
    public_key = models.TextField(max_length=2000, validators=[validate_ssh_public_key])

    class Meta(object):
        unique_together = ('user', 'name')

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        def get_fingerprint(public_key):
            # How to get fingerprint from ssh key:
            # http://stackoverflow.com/a/6682934/175349
            # http://www.ietf.org/rfc/rfc4716.txt Section 4.
            import base64
            import hashlib

            key_body = base64.b64decode(public_key.strip().split()[1].encode('ascii'))
            fp_plain = hashlib.md5(key_body).hexdigest()
            return ':'.join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))

        # Fingerprint is always set based on public_key
        try:
            self.fingerprint = get_fingerprint(self.public_key)
        except IndexError:
            raise ValueError('Public key format is incorrect. Fingerprint calculation has failed.')

        if update_fields and 'public_key' in update_fields and 'fingerprint' not in update_fields:
            update_fields.append('fingerprint')

        super(SshPublicKey, self).save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return self.name


class SynchronizationStates(object):
    SYNCING_SCHEDULED = 'u'
    SYNCING = 'U'
    IN_SYNC = 's'
    ERRED = 'e'

    CHOICES = (
        (SYNCING_SCHEDULED, _('Sync Scheduled')),
        (SYNCING, _('Syncing')),
        (IN_SYNC, _('In Sync')),
        (ERRED, _('Erred')),
    )


class SynchronizableMixin(models.Model):
    class Meta(object):
        abstract = True

    state = FSMField(
        max_length=1,
        default=SynchronizationStates.SYNCING_SCHEDULED,
        choices=SynchronizationStates.CHOICES,
    )

    @transition(field=state, source=SynchronizationStates.SYNCING_SCHEDULED, target=SynchronizationStates.SYNCING)
    def begin_syncing(self):
        pass

    @transition(field=state, source=SynchronizationStates.IN_SYNC, target=SynchronizationStates.SYNCING_SCHEDULED)
    def schedule_syncing(self):
        pass

    @transition(field=state, source=SynchronizationStates.SYNCING, target=SynchronizationStates.IN_SYNC)
    def set_in_sync(self):
        pass

    @transition(field=state, source='*', target=SynchronizationStates.ERRED)
    def set_erred(self):
        pass


# Signal handlers
@receiver(signals.post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
