import string
import re


MAX_QUERY_STRING_LENGTH = 255

re_punctuation = re.compile('[' + string.punctuation + ']')

def normalise_query_string(query_string):
    # Truncate query string
    if len(query_string) > MAX_QUERY_STRING_LENGTH:
        query_string = query_string[:MAX_QUERY_STRING_LENGTH]
    # Convert query_string to lowercase
    query_string = query_string.lower()

    # Convert punctuation characters to spaces
    query_string = re_punctuation.sub(' ', query_string)

    # Remove double spaces
    query_string = ' '.join(query_string.split())

    return query_string
