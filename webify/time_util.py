import datetime

current_time = datetime.datetime.now()
print(current_time)

from dateutil import parser

time_a = 'April 23, 2020'
print(parser.parse(time_a))

time_b = '24 April   2020 9am'
print(parser.parse(time_b).date())

time_d = '2020-01-22'
print(parser.parse(time_d).time())
