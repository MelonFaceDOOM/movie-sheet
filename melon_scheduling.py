import datetime
from operator import itemgetter


# TODO: make it so u can't schedule the past
# TODO: make it so end date can't be before start date

def parse_time_range(start_raw, end_raw=None):
    start = parse_datetime(start_raw)
    if not end_raw:
        # make a range out of just the start timestmap (i.e. 2020-07-19 becomes 2020-07-19 00:00 - 2020-07-19 23:59)
        end = parse_datetime(start_raw, end_of_day=True)
    else:
        end = parse_datetime(end_raw)

    return min(start, end), max(start, end)


def parse_datetime(datetime_raw, end_of_day=False):
    """If a date is provided without a time, time will based on end_of_day (00:00 or 23:59)"""

    words = datetime_raw.split(" ")
    date_raw = words[0]
    time_raw = None
    if len(words) == 1:
        pass
    else:
        for word in words[1:]:
            if parse_date(date_raw + " " + word):
                date_raw += " " + word
            else:
                time_start = words.index(word)
                time_raw = " ".join(words[time_start:])
                break

    if not time_raw:
        date = parse_date(date_raw)
        if end_of_day:
            time = datetime.time(23, 59)
        else:
            time = datetime.time(0)
    else:
        time = parse_time(time_raw)
        date = parse_date(date_raw)
    return datetime.datetime.combine(date, time)


def parse_date_with_timerange(date_with_timerange_raw):
    """accepts date + time range (i.e. "feb 7 9pm-10pm")"""
    words = date_with_timerange_raw.split(" ")
    date_raw = words[0]
    if len(words) < 2:
        return None, None
    else:
        for word in words[1:]:
            if parse_date(date_raw + " " + word):
                date_raw += " " + word
            else:
                # confirms that there is only 1 item in list after date (i.e. the timerange)
                if len(words) != words.index(word) + 1:
                    return None, None
                time_range = words[-1]
                break

    time_div = time_range.find("-")
    if not time_div:
        return None, None

    start_time_raw = time_range[:time_div]
    end_time_raw = time_range[time_div + 1:]
    start_time = parse_time(start_time_raw)
    end_time = parse_time(end_time_raw)
    date = parse_date(date_raw)

    start_datetime = datetime.datetime.combine(date, start_time)
    end_datetime = datetime.datetime.combine(date, end_time)
    return start_datetime, end_datetime


def parse_date(date_raw):
    """accepted formats: 2020-04-16, may 24, sat[urday], 'today', 'tomorrow'"""
    if date_raw.lower() == "today":
        return datetime.date.today()
    if date_raw.lower() == "tomorrow":
        return datetime.date.today() + datetime.timedelta(1)

    weekday = parse_weekday(date_raw)
    if type(weekday) == int:
        today = datetime.date.today()
        return today + datetime.timedelta((weekday - 1 - today.weekday()) % 7 + 1)

    month_day = parse_month_day(date_raw)
    if month_day:
        current_year = datetime.date.today().year
        current_month = datetime.date.today().month
        current_day = datetime.date.today().day
        if month_day[0] > current_month or \
                month_day[0] == current_month and month_day[1] >= current_day:
            return datetime.datetime(year=current_year, month=month_day[0], day=month_day[1])
        if month_day[0] < current_month or \
                month_day[0] == current_month and month_day[1] < current_day:
            return datetime.datetime(year=current_year + 1, month=month_day[0], day=month_day[1])

    date_formats = ['%Y/%m/%d', '%Y-%m-%d']
    for date_format in date_formats:
        try:
            date = datetime.datetime.strptime(date_raw, date_format).date()
            return date
        except ValueError:
            pass
    return None


def parse_time(time_raw):
    time_formats = ['%I:%M%p', '%I%p', '%I %p', '%H:%M', '%H']
    for tf in time_formats:
        try:
            time = datetime.datetime.strptime(time_raw.strip(), tf).time()
            return time
        except ValueError:
            pass
    raise ValueError('time format not recognized')


def parse_weekday(weekday):
    if len(weekday) < 2:
        return False
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for day in weekdays:
        if day.startswith(weekday.lower()):
            return weekdays.index(day)
    return False


def parse_month_day(month_day):
    """if format is "feb[ruary] 15", returns [2, 15]"""
    space = month_day.find(" ")
    if space == -1:
        return False
    month = month_day[:space]
    if len(month) < 3:
        return False
    months = ['januray', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november', 'december']
    for real_month in months:
        if real_month.startswith(month.lower()):
            month = months.index(real_month) + 1
            break
    else:
        return False
    day = month_day[space + 1:]
    try:
        day = int(day)
    except ValueError:
        return False
    return [month, day]


def build_time_row(hour):
    time_row = str(hour) + " " * (3 - len(str(hour)))
    return time_row

class Event:
    def __init__(self, name):
        self.name = name
        self.participants = []
        self.suggested_times = []

    def add_participant(self, participant_name):
        """returns existing participant with matching name, or adds new participant then returns that"""
        for event_participant in self.participants:
            if event_participant.name == participant_name:
                return event_participant
        participant = Participant(participant_name, self)
        self.participants.append(participant)
        return participant

    def find_participant(self, participant_name):
        for event_participant in self.participants:
            if event_participant.name == participant_name:
                return event_participant
        return None

    def remove_participant(self, participant):
        if type(participant) != Participant:
            raise TypeError("participant must be a Participant object")

        if participant in self.participants:
            self.participants.remove(participant)

    def all_times(self):
        times = []
        for p in self.participants:
            for t in p.times_available:
                times.append(t)
        return times

    def most_overlapped_time(self):
        list_of_pairs = []
        for participant in self.participants:
            for time_available in participant.times_available:
                list_of_pairs.append(time_available)
        if not list_of_pairs:
            return None, None
        # primary sort starts ascending
        # secondary sort ends descending
        list_of_pairs.sort(key=itemgetter(1), reverse=True)
        list_of_pairs.sort(key=itemgetter(0))
        overlap = [list_of_pairs[0][0], list_of_pairs[0][1]]
        overlapping_pairs = [list_of_pairs[0]]
        max_overlap = [1]
        max_overlapping_pairs = [list_of_pairs[0]]
        for pair in list_of_pairs[1:]:
            if pair[0] < overlap[1]:
                overlapping_pairs.append(pair)
                overlap[0] = pair[0]
                overlap[1] = min(pair[1], overlap[1])
            # 2nd half of 'or' executes this code if this is the last loop, to do the final overlap comparison
            if pair[0] >= overlap[1] or list_of_pairs.index(pair) == len(list_of_pairs) - 1:
                if len(overlapping_pairs) > len(max_overlapping_pairs):
                    max_overlapping_pairs = overlapping_pairs
                    max_overlap = overlap

                if len(overlapping_pairs) == len(max_overlapping_pairs):
                    if max_overlap[1] - max_overlap[0] < overlap[1] - overlap[0]:
                        max_overlapping_pairs = overlapping_pairs
                        max_overlap = overlap
                overlap = [pair[0], pair[1]]
                overlapping_pairs = []
        return max_overlap, max_overlapping_pairs

    def summary(self):
        max_width = 46  # discord chat width is 46 characters on my phone.

        # get list of all days where there is any availability
        days = []
        for start, end in self.all_times():
            start = start.date()
            end = end.date()
            days_in_range = [start + datetime.timedelta(days=x) for x in range((end-start).days + 1)]
            for day in days_in_range:
                if day not in days:
                    days.append(day)

        # find longest truncated participant names that fit in available width.
        # excess_characters will also be used throughout the function.
        remaining_space = max_width - len(build_time_row(0))
        # TODO: if it's not possible to fit all names (i.e. if there are >22 participants), split this into two parts.
        participants = self.participants
        participant_names = [p.name for p in participants]
        excess_characters = len(" ".join(participant_names)) - remaining_space
        while excess_characters > 0:
            longest_name = max(participant_names, key=len)
            starting_max_len = len(longest_name) - 1
            for i, participant in enumerate(participant_names):
                participant_names[i] = participant[:starting_max_len]
                excess_characters = len(" ".join(participant_names)) - remaining_space
                if excess_characters <= 0:
                    break

        # start building the output column for each day
        output_columns = []
        for day in days:
            day_output_column = ""
            date_title = datetime.datetime.strftime(day, '%a! %b %d? %Y......')
            total_length = max_width + excess_characters  # excess will be 0 or negative
            date_left_spaces = int((total_length - len(date_title) + 1) / 2)
            date_right_spaces = int((total_length - len(date_title)) / 2)
            day_output_column += " " * date_left_spaces + date_title + " " * date_right_spaces

            day_output_column += "\n" + " " * len(
                build_time_row(0))  # add a newline and sufficient spaces for the time column
            for participant in participant_names:
                day_output_column += participant + " "
            day_output_column = day_output_column[:-1] + "\n"  # remove the final excess space and add newline

            # add one line for each participant
            for hour in range(0, 24):
                day_output_column += build_time_row(hour)  # remove the final excess space and add newline
                hour_start = datetime.datetime(day.year, day.month, day.day, hour, 0)
                hour_end = datetime.datetime(day.year, day.month, day.day, hour, 59)
                for i, participant in enumerate(participants):
                    availability = participant.is_available(hour_start, hour_end)
                    time_markers = {'voted': 'O',
                                    'voted partially': 'o',
                                    'available': 'x',
                                    'available partially': 'X',
                                    'no': '|', }
                    time_marker = time_markers[availability]
                    truncated_name = participant_names[i]
                    name_left_spaces = int((len(truncated_name) - 1) / 2)
                    name_right_spaces = int((len(truncated_name)) / 2) + 1
                    day_output_column += " " * name_left_spaces + time_marker + " " * name_right_spaces
                day_output_column = day_output_column[:-1] + "\n"  # remove the final excess space and add newline
            output_columns.append(day_output_column)
        return output_columns


class Participant:
    def __init__(self, name, event):
        self.name = name
        self.times_available = []
        self.event = event
        if type(event) != Event:
            raise TypeError("event must be an Event object")

    def __repr__(self):
        return self.name

    def add_availability(self, start_time, end_time):
        if type(start_time) != datetime.datetime or type(end_time) != datetime.datetime:
            raise TypeError("start_time and end_time must be Time objects")
        if not self.times_available:
            self.times_available.append((start_time, end_time))
        else:
            # check for overlapping times
            for time_pair in self.times_available:
                # no overlap
                if start_time > time_pair[1] or end_time < time_pair[0]:
                    continue
                # overlap
                else:
                    start_time = min(time_pair[0], start_time)
                    end_time = max(time_pair[1], end_time)
                    self.times_available.remove(time_pair)
            self.times_available.append((start_time, end_time))

    def remove_availability(self, start_time, end_time):
        if type(start_time) != datetime.datetime or type(end_time) != datetime.datetime:
            raise TypeError("start_time and end_time must be Time objects")

        for time_pair in self.times_available:
            # no overlap
            if start_time > time_pair[1] or end_time < time_pair[0]:
                continue
            # overlap
            elif start_time < time_pair[0] and end_time < time_pair[1]:
                self.times_available.remove((time_pair[0], time_pair[1]))
                self.times_available.append((end_time, time_pair[1]))
            elif start_time > time_pair[0] and end_time > time_pair[1]:
                self.times_available.remove((time_pair[0], time_pair[1]))
                self.times_available.append((time_pair[0], start_time))
            elif start_time > time_pair[0] and end_time < time_pair[1]:
                self.times_available.remove((time_pair[0], time_pair[1]))
                self.times_available.append((time_pair[0], start_time))
                self.times_available.append((end_time, time_pair[1]))
            elif start_time <= time_pair[0] and end_time >= time_pair[0]:
                self.times_available.remove((time_pair[0], time_pair[1]))

    def suggest_time(self, start_time, end_time):
        # this same func is also used for voting for a suggested time.
        if type(start_time) != datetime.datetime or type(end_time) != datetime.datetime:
            raise TypeError("start_time and end_time must be Time objects")
        for suggested_time in self.event.suggested_times:
            if suggested_time.start_time == start_time and suggested_time.end_time == end_time:
                suggested_time.voters.append(self)
                break
        else:
            suggested_time = SuggestedTime(self, start_time, end_time)
            self.event.suggested_times.append(suggested_time)
            self.add_availability(suggested_time.start_time, suggested_time.end_time)

    def unsuggest_time(self, start_time, end_time):
        if type(start_time) != datetime.datetime or type(end_time) != datetime.datetime:
            raise TypeError("start_time and end_time must be Time objects")
        for suggested_time in self.event.suggested_times:
            if suggested_time.start_time == start_time and suggested_time.end_time == end_time:
                suggested_time.voters.remove(self)
                if len(suggested_time.voters) == 0:
                    self.event.suggested_times.remove(suggested_time)
                break

    def is_available(self, start_time, end_time):
        """returns:
        voted: participant has voted for a time that fully includes this time range
        voted partially: participant has voted for a time that partially includes this time range
        available: participant has not voted for this time range, but is available
        available partially: participant is available for part of this time range
        no: participant has not voted for and is not available for this time range"""

        suggested_times = self.event.suggested_times
        suggested_times_with_participant = [s for s in suggested_times if self in s.voters]
        for suggested_time in suggested_times_with_participant:
            if suggested_time.start_time <= start_time and suggested_time.end_time >= end_time:
                return 'voted'
            elif suggested_time.start_time < end_time and suggested_time.end_time > start_time:
                return 'voted partially'
        for time_available in self.times_available:
            if time_available[0] <= start_time and time_available[1] >= end_time:
                return 'available'
            elif time_available[0] < end_time and time_available[1] > start_time:
                return 'available partially'
        return 'no'


class SuggestedTime:
    def __init__(self, suggesting_participant, start_time, end_time):
        if type(start_time) != datetime.datetime or type(end_time) != datetime.datetime:
            raise TypeError("start_time and end_time must be Time objects")
        self.event = suggesting_participant.event
        self.voters = [suggesting_participant]
        self.start_time = min(start_time, end_time)
        self.end_time = max(start_time, end_time)

    def check_availability(self):
        available_participants = []
        for participant in self.event.participants:
            for time_pair in participant.times_available:
                if self.start_time >= time_pair[0] and self.end_time <= time_pair[1]:
                    available_participants.append(participant)
                    break
        return available_participants
