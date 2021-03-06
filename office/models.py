# office/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from exception.models import handle_exception, handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_we_vote_id_last_contest_office_integer, fetch_site_unique_id_prefix
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_state_from_ocd_division_id, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


class ContestOffice(models.Model):
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "off", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_contest_office_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this contest office", max_length=255, default=None, null=True,
        blank=True, unique=True)
    # The name of the office for this contest.
    office_name = models.CharField(verbose_name="name of the office", max_length=255, null=False, blank=False)
    # The offices' name as passed over by Google Civic. We save this so we can match to this office even
    # if we edit the office's name locally.
    google_civic_office_name = models.CharField(verbose_name="office name exactly as received from google civic",
                                                max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=False, blank=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    maplight_id = models.CharField(
        verbose_name="maplight unique identifier", max_length=255, null=True, blank=True, unique=True)
    ballotpedia_id = models.CharField(
        verbose_name="ballotpedia unique identifier", max_length=255, null=True, blank=True)
    wikipedia_id = models.CharField(verbose_name="wikipedia unique identifier", max_length=255, null=True, blank=True)
    # vote_type (ranked choice, majority)
    # The number of candidates that a voter may vote for in this contest.
    number_voting_for = models.CharField(verbose_name="google civic number of candidates to vote for",
                                         max_length=255, null=True, blank=True)
    # The number of candidates that will be elected to office in this contest.
    number_elected = models.CharField(verbose_name="google civic number of candidates who will be elected",
                                      max_length=255, null=True, blank=True)

    # State code
    state_code = models.CharField(verbose_name="state this office serves", max_length=2, null=True, blank=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="district name", max_length=255, null=True, blank=True)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=255, null=True, blank=True)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_id = models.CharField(verbose_name="google civic district id", max_length=255, null=True, blank=True)

    # The levels of government of the office for this contest. There may be more than one in cases where a
    # jurisdiction effectively acts at two different levels of government; for example, the mayor of the
    # District of Columbia acts at "locality" level, but also effectively at both
    # "administrative-area-2" and "administrative-area-1".
    contest_level0 = models.CharField(verbose_name="google civic level, option 0",
                                      max_length=255, null=True, blank=True)
    contest_level1 = models.CharField(verbose_name="google civic level, option 1",
                                      max_length=255, null=True, blank=True)
    contest_level2 = models.CharField(verbose_name="google civic level, option 2",
                                      max_length=255, null=True, blank=True)

    # ballot_placement: We store ballot_placement in the BallotItem table instead because it is different for each voter

    # A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = models.CharField(verbose_name="google civic primary party",
                                                 max_length=255, null=True, blank=True)
    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    office_description = models.CharField(verbose_name="office description", max_length=255, null=True, blank=True)
    office_is_partisan = models.BooleanField(verbose_name="office is_partisan", default=False)

    def get_office_state(self):
        if positive_value_exists(self.state_code):
            return self.state_code
        else:
            # Pull this from ocdDivisionId
            if positive_value_exists(self.ocd_division_id):
                ocd_division_id = self.ocd_division_id
                return extract_state_from_ocd_division_id(ocd_division_id)
            else:
                return ''

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_contest_office_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "off" = tells us this is a unique id for a ContestOffice
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}off{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ContestOffice, self).save(*args, **kwargs)


class ContestOfficeManager(models.Model):

    def __unicode__(self):
        return "ContestOfficeManager"

    def retrieve_contest_office_from_id(self, contest_office_id):
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id)

    def retrieve_contest_office_from_we_vote_id(self, contest_office_we_vote_id):
        contest_office_id = 0
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, contest_office_we_vote_id)

    def retrieve_contest_office_from_maplight_id(self, maplight_id):
        contest_office_id = 0
        contest_office_we_vote_id = ''
        contest_office_manager = ContestOfficeManager()
        return contest_office_manager.retrieve_contest_office(contest_office_id, contest_office_we_vote_id, maplight_id)

    def fetch_contest_office_id_from_maplight_id(self, maplight_id):
        contest_office_id = 0
        contest_office_we_vote_id = ''
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office(
            contest_office_id, contest_office_we_vote_id, maplight_id)
        if results['success']:
            return results['contest_office_id']
        return 0

    def fetch_contest_office_we_vote_id_from_id(self, contest_office_id):
        maplight_id = 0
        contest_office_we_vote_id = ''
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office(
            contest_office_id, contest_office_we_vote_id, maplight_id)
        if results['success']:
            return results['contest_office_we_vote_id']
        return 0

    def update_or_create_contest_office(self, office_we_vote_id, maplight_id, google_civic_election_id,
                                        office_name, state_code, district_id, updated_contest_office_values):
        """
        Either update or create an office entry.
        """
        exception_multiple_object_returned = False
        new_office_created = False
        contest_office_on_stage = ContestOffice()
        success = False
        status = ""
        office_updated = False

        if not google_civic_election_id:
            success = False
            status += 'MISSING_GOOGLE_CIVIC_ELECTION_ID '
        # DALE 2016-05-10 Since we are allowing offices to be created prior to Google Civic data
        # being available, we need to remove our reliance on district_id or district_name
        # elif not (district_id or district_name):
        #     success = False
        #     status = 'MISSING_DISTRICT_ID'
        elif not office_name:
            success = False
            status += 'MISSING_OFFICE_NAME '
        elif positive_value_exists(office_we_vote_id):
            try:
                contest_office_on_stage, new_office_created = ContestOffice.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    we_vote_id__iexact=office_we_vote_id,
                    defaults=updated_contest_office_values)
                office_updated = not new_office_created
                success = True
                status += 'CONTEST_OFFICE_SAVED '
            except ContestOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND '
                exception_multiple_object_returned = True
            except ContestOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        elif positive_value_exists(maplight_id):
            try:
                contest_office_on_stage, new_office_created = ContestOffice.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    maplight_id__exact=maplight_id,
                    defaults=updated_contest_office_values)
                office_updated = not new_office_created
                success = True
                status += 'CONTEST_OFFICE_SAVED '
            except ContestOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND '
                exception_multiple_object_returned = True
            except ContestOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_MAPLIGHT_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        else:
            # Given we might have the office listed by google_civic_office_name
            # OR office_name, we need to check both before we try to create a new entry
            contest_office_found = False
            try:
                # TODO DALE Note that Vermont data in 2016 did not provide district_id. The unique value was in the
                # district_name. So all "VT State Senator" candidates were lumped into a single office. But I believe
                # Presidential races don't have either district_id or district_name, so we can't require one.
                # Perhaps have a special case for "district" -> "scope": "stateUpper"/"stateLower"
                # vs. "scope": "statewide"
                if positive_value_exists(district_id):
                    contest_office_on_stage = ContestOffice.objects.get(
                        google_civic_election_id__exact=google_civic_election_id,
                        google_civic_office_name__iexact=office_name,
                        district_id__exact=district_id,
                        state_code__iexact=state_code
                    )
                else:
                    contest_office_on_stage = ContestOffice.objects.get(
                        google_civic_election_id__exact=google_civic_election_id,
                        google_civic_office_name__iexact=office_name,
                        state_code__iexact=state_code
                    )
                contest_office_found = True
                success = True
                status += 'CONTEST_OFFICE_SAVED '
            except ContestOffice.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_GOOGLE_CIVIC_OFFICE_NAME '
                exception_multiple_object_returned = True
            except ContestOffice.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_OFFICE_NOT_FOUND "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_OFFICE_BY_GOOGLE_CIVIC_OFFICE_NAME ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

            if not contest_office_found and not exception_multiple_object_returned:
                # Try to find record based on office_name (instead of google_civic_office_name)
                try:
                    if positive_value_exists(district_id):
                        contest_office_on_stage = ContestOffice.objects.get(
                            google_civic_election_id__exact=google_civic_election_id,
                            office_name__iexact=office_name,
                            district_id__exact=district_id,
                            state_code__iexact=state_code
                        )
                    else:
                        contest_office_on_stage = ContestOffice.objects.get(
                            google_civic_election_id__exact=google_civic_election_id,
                            office_name__iexact=office_name,
                            state_code__iexact=state_code
                        )
                    contest_office_found = True
                    success = True
                    status += 'CONTEST_OFFICE_SAVED '
                except ContestOffice.MultipleObjectsReturned as e:
                    success = False
                    status += 'MULTIPLE_MATCHING_CONTEST_OFFICES_FOUND_BY_OFFICE_NAME '
                    exception_multiple_object_returned = True
                except ContestOffice.DoesNotExist:
                    exception_does_not_exist = True
                    status += "RETRIEVE_OFFICE_NOT_FOUND "
                except Exception as e:
                    status += 'FAILED retrieve_all_offices_for_upcoming_election ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

            if exception_multiple_object_returned:
                # We can't proceed because there is an error with the data
                success = False
            elif contest_office_found:
                # Update record
                try:
                    for key, value in updated_contest_office_values.items():
                        if hasattr(contest_office_on_stage, key):
                            setattr(contest_office_on_stage, key, value)
                    contest_office_on_stage.save()
                    office_updated = True
                    new_office_created = False
                    success = True
                except Exception as e:
                    status += 'FAILED_TO_UPDATE_CONTEST_OFFICE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
            else:
                # Create record
                try:
                    contest_office_on_stage = ContestOffice.objects.create()
                    for key, value in updated_contest_office_values.items():
                        if hasattr(contest_office_on_stage, key):
                            setattr(contest_office_on_stage, key, value)
                    contest_office_on_stage.save()
                    office_updated = False
                    new_office_created = True
                    success = True
                except Exception as e:
                    status += 'FAILED_TO_CREATE_CONTEST_OFFICE ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'new_office_created':       new_office_created,
            'contest_office':           contest_office_on_stage,
            'saved':                    new_office_created or office_updated,
            'updated':                  office_updated,
            'not_processed':            True if not success else False,
        }
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_contest_office(self, contest_office_id, contest_office_we_vote_id='', maplight_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        contest_office_on_stage = ContestOffice()

        try:
            if positive_value_exists(contest_office_id):
                contest_office_on_stage = ContestOffice.objects.get(id=contest_office_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_ID"
            elif positive_value_exists(contest_office_we_vote_id):
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id=contest_office_we_vote_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_WE_VOTE_ID"
            elif positive_value_exists(maplight_id):
                contest_office_on_stage = ContestOffice.objects.get(maplight_id=maplight_id)
                contest_office_id = contest_office_on_stage.id
                contest_office_we_vote_id = contest_office_on_stage.we_vote_id
                status = "RETRIEVE_OFFICE_FOUND_BY_MAPLIGHT_ID"
            else:
                status = "RETRIEVE_OFFICE_SEARCH_INDEX_MISSING"
        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status = "RETRIEVE_OFFICE_MULTIPLE_OBJECTS_RETURNED"
        except ContestOffice.DoesNotExist:
            exception_does_not_exist = True
            status = "RETRIEVE_OFFICE_NOT_FOUND"

        results = {
            'success':                      True if convert_to_int(contest_office_id) > 0 else False,
            'status':                       status,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
            'contest_office_found':         True if convert_to_int(contest_office_id) > 0 else False,
            'contest_office_id':            convert_to_int(contest_office_id),
            'contest_office_we_vote_id':    contest_office_we_vote_id,
            'contest_office':               contest_office_on_stage,
        }
        return results

    def fetch_contest_office_id_from_we_vote_id(self, contest_office_we_vote_id):
        """
        Take in contest_office_we_vote_id and return internal/local-to-this-database contest_office_id
        :param contest_office_we_vote_id:
        :return:
        """
        contest_office_id = 0
        try:
            if positive_value_exists(contest_office_we_vote_id):
                contest_office_on_stage = ContestOffice.objects.get(we_vote_id=contest_office_we_vote_id)
                contest_office_id = contest_office_on_stage.id

        except ContestOffice.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)

        except ContestOffice.DoesNotExist:
            contest_office_id = 0

        return contest_office_id


class ContestOfficeListManager(models.Model):
    """
    This is a class to make it easy to retrieve lists of Offices
    """

    def __unicode__(self):
        return "ContestOfficeListManager"

    def retrieve_all_offices_for_upcoming_election(self, google_civic_election_id=0, state_code="",
                                                   return_list_of_objects=False):
        office_list = []
        return self.retrieve_offices(google_civic_election_id, state_code, office_list, return_list_of_objects)

    def retrieve_offices_by_list(self, office_list, return_list_of_objects=False):
        google_civic_election_id = 0
        state_code = ""
        return self.retrieve_offices(google_civic_election_id, state_code, office_list, return_list_of_objects)

    def retrieve_offices(self, google_civic_election_id=0, state_code="", office_list=[],
                         return_list_of_objects=False):
        office_list_objects = []
        office_list_light = []
        office_list_found = False

        try:
            office_queryset = ContestOffice.objects.all()
            if positive_value_exists(google_civic_election_id):
                office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
            else:
                # TODO Limit this search to upcoming_elections only
                pass
            if positive_value_exists(state_code):
                office_queryset = office_queryset.filter(state_code__iexact=state_code)
            if len(office_list):
                office_queryset = office_queryset.filter(
                    we_vote_id__in=office_list)
            office_queryset = office_queryset.order_by("office_name")
            office_list_objects = office_queryset

            if len(office_list_objects):
                office_list_found = True
                status = 'OFFICES_RETRIEVED'
                success = True
            else:
                status = 'NO_OFFICES_RETRIEVED'
                success = True
        except ContestOffice.DoesNotExist:
            # No offices found. Not a problem.
            status = 'NO_OFFICES_FOUND_DoesNotExist'
            office_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_all_offices_for_upcoming_election ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if office_list_found:
            for office in office_list_objects:
                one_office = {
                    'ballot_item_display_name': office.office_name,
                    'measure_we_vote_id':       '',
                    'office_we_vote_id':        office.we_vote_id,
                    'candidate_we_vote_id':     '',
                }
                office_list_light.append(one_office.copy())

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'office_list_found':        office_list_found,
            'office_list_objects':      office_list_objects if return_list_of_objects else [],
            'office_list_light':        office_list_light,
        }
        return results

    def retrieve_possible_duplicate_offices(self, google_civic_election_id, office_name,
                                            state_code, we_vote_id_from_master=''):
        """
        Find offices that match another office in all critical fields other than we_vote_id_from_master
        :param google_civic_election_id:
        :return:
        """
        office_list_objects = []
        office_list_found = False

        try:
            office_queryset = ContestOffice.objects.all()
            office_queryset = office_queryset.filter(google_civic_election_id=google_civic_election_id)
            office_queryset = office_queryset.filter(office_name__iexact=office_name)  # Case doesn't matter
            office_queryset = office_queryset.filter(state_code__iexact=state_code)  # Case doesn't matter
            # office_queryset = office_queryset.filter(district_id__exact=district_id)
            # office_queryset = office_queryset.filter(district_name__iexact=district_name)  # Case doesn't matter

            # Ignore we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                office_queryset = office_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            office_list_objects = office_queryset

            if len(office_list_objects):
                office_list_found = True
                status = 'OFFICES_RETRIEVED'
                success = True
            else:
                status = 'NO_OFFICES_RETRIEVED'
                success = True
        except ContestOffice.DoesNotExist:
            # No offices found. Not a problem.
            status = 'NO_OFFICES_FOUND_DoesNotExist'
            office_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_offices ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'office_list_found':        office_list_found,
            'office_list':              office_list_objects,
        }
        return results
