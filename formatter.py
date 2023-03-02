# Formatter module
# This module format and return string type arguments in desired format


# Function remove_first_last_lines removes first and last lines in a multiple line 
# input args and returns remaining lines. Returns list ['FALSE'] if args is corrupted
# by syslogd message
def remove_first_last_lines(args):
	input_list = args.split('\n')
	if str(input_list).find('syslogd') != -1:
		return ['FALSE']
	elif len(input_list) <= 2:
		return []
	else:
		return input_list[1:-1]