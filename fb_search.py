from __future__ import unicode_literals
import requests
import json
import time
import calendar
import os
import errno
import youtube_dl as dl


ACCESS_TOKEN = ' '   # Unique Graph API Access Token
BASE_URL = 'https://graph.facebook.com/v2.9/'
VIDEO_BASE_URL = 'https://www.facebook.com/video.php?v='

VERBOSE = True
JSON_VERBOSE_PAGE = False
JSON_VERBOSE_VIDEO = False
RECURSION_MAX = 999
REQUEST_RETRY_MAX = 999

V_MAXDURATION = 120
V_PUBLISHEDAFTER = '2017-01-01 00:00:00'


#### HELPER FUNCTIONS ####

def submit_request(url, params_raw, next_page_addon, req_num=1):
    """
    Submits an HTTP request

    Returns:
    JSON object
    """
    if next_page_addon is not None:
        params_raw.append(('after', next_page_addon))

    request = requests.get(url, params=params_raw, headers={'Authorization': 'Bearer {}'.format(ACCESS_TOKEN)})
    req_json = request.json()

    if req_json.get('error'):
        if req_json['error']['message'] == "Please reduce the amount of data you're asking for, then retry your request":
            if req_num > REQUEST_RETRY_MAX:
                print 'Maximum request retries reached | Check API request'
                return None

            if VERBOSE:
                print 'WARNING: Graph API error'
                print 'Reducing data range | Retrying request'
                print ''

            new_params = params_raw
            new_params[1] = ('since', params_raw[1][1] + 1500000.0)

            return submit_request(url, new_params, next_page_addon, req_num=req_num + 1)

    if VERBOSE:
        print 'Full Request: ' + request.url
        print 'Response Status Code: ' + str(request.status_code)

    return req_json


def date2unix(date):
    """
    Converts date to unix timestamp

    Arguments:
    date -- string in format 'yyyy-mm-dd HH:MM:SS'

    Returns:
    Unix timestamp as floating point number
    """
    struct_time = time.strptime(date, '%Y-%m-%d %H:%M:%S')
    return calendar.timegm(struct_time)


def make_directory(path):
    """
    Creates directory if it does not already exist

    Arguments:
    path -- directory path name

    Returns:
    None
    """
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


#### PAGE FUNCTIONS ####

def search_pages(query, page_max, next_page_addon=None, recur=0, count=0):
    """
    Searches for Facebook pages based on search query

    Arguments:
    query -- search query as string
    page_max -- maximum number of pages wanted
    next_page_addon -- url addon for next page if multiple pages of pages
    recur -- integer indicating number of recursions
    count -- integer representing number of pages found

    Returns:
    List of pages represented as JSON object
    """
    if recur >= RECURSION_MAX:
        print 'WARNING: recursion limit reached'

    if count >= page_max:
        return []

    if page_max > 50:
        limit = 50
    else:
        limit = page_max

    params_raw = [('q', query),
                  ('type', 'page'),
                  ('limit', limit)]
    request = submit_request(BASE_URL + 'search', params_raw, next_page_addon)
    data = request.get('data')

    if (data is None) or (len(data) == 0):
        return []

    if request.get('paging').get('next'):
        page_addon = request.get('paging').get('cursors').get('after')
        data.extend(search_pages(query, page_max, next_page_addon=page_addon, recur=recur + 1, count=count + limit))

    data_detailed = []
    for page in data:
        data_detailed.append(get_page_details(page, query))

    results = [page for page in data_detailed if page is not None]
    if JSON_VERBOSE_PAGE:
        print json.dumps(results, indent=4, sort_keys=True)

    return results


def get_page_details(page, query):
    """
    Gives details of page

    Arguments:
    page -- page represented as JSON object
    query -- search query as string

    Returns:
    Page details
    """
    page_id = page['id']
    params_raw = [('fields', 'about,name,id,is_verified,link,verification_status')]
    page_obj = submit_request(BASE_URL + page_id, params_raw, None)

    try:
        return {'query': query,
                'name': page_obj['name'],
                'about': page_obj['about'],
                'page_id': page_obj['id'],
                'is_verified': page_obj['is_verified'],
                'verification_status': page_obj['verification_status']}
    except KeyError:
        return None


def is_verified_page(page):
    """
    Determines whether the page is a Facebook verified page

    Arguments:
    page -- page represented as JSON object

    Returns:
    Boolean for verification status
    """
    return page['is_verified']


def select_page(query, batch_size):
    """
    Searches for a batch of pages and picks best match

    Arguments:
    query -- search query as string
    batch_size -- number of channels to analyze

    Returns:
    Chosen channel object
    """
    candidates = search_pages(query, batch_size)
    if len(candidates) == 0:
        print 'select_page: no page match found --> ' + query
        return None

    for page in candidates:
        if is_verified_page(page):
            return page

    return candidates[0]


#### VIDEO FUNCTIONS ####

def search_page_videos(page_id, vid_max, next_page_addon=None, recur=0, count=0):
    """
    Searches page for videos

    Arguments:
    page_id -- page id as string
    vid_max -- maximum number of videos wanted per page
    next_page_addon -- url addon for next page if multiple pages of videos
    recur -- integer indicating number of recursions
    count -- integer representing number of pages found

    Returns:
    List of video json objects for specified page
    """
    if recur >= RECURSION_MAX:
        print 'WARNING: recursion limit reached'

    if count >= vid_max:
        return []

    if vid_max > 50:
        limit = 50
    else:
        limit = vid_max

    params_raw = [('limit', limit),
                  ('since', date2unix(V_PUBLISHEDAFTER))]
    request = submit_request(BASE_URL + page_id + '/videos', params_raw, next_page_addon)
    data = request.get('data')

    if (data is None) or (len(data) == 0):
        return []

    if request.get('paging').get('next'):
        page_addon = request.get('paging').get('cursors').get('after')
        data.extend(search_page_videos(page_id, vid_max, next_page_addon=page_addon, recur=recur + 1, count=count + limit))

    data_detailed = map(get_vid_details, data)

    results = [video for video in data_detailed if video['video']['length'] <= V_MAXDURATION]
    if JSON_VERBOSE_VIDEO:
        print json.dumps(results, indent=4, sort_keys=True)

    return results


def get_vid_details(video):
    """
    Provides more video details

    Arguments:
    video -- JSON object representing video

    Returns:
    Video details
    """
    video_id = video['id']
    params_raw = [('fields', 'description,created_time,id,content_category,from,length,permalink_url,picture,source,status,title,thumbnails{height,scale,uri,width,is_preferred}')]
    request = submit_request(BASE_URL + video_id, params_raw, None)

    if request is None:
        return None

    details = {'page': {'page_name': request['from']['name'],
                        'page_id': request['from']['id']
                        },
               'video': {'video_id': request['id'],
                         'created_time': request['created_time'],
                         'content_category': request['content_category'],
                         'length': request['length'],
                         'permalink_url': request['permalink_url'],
                         'picture': request['picture'],
                         'source': VIDEO_BASE_URL + request['id'],
                         'video_status': request['status']['video_status']
                         }
               }

    if request.get('title'):
        details['video']['video_title'] = request['title']

    if request.get('description'):
        details['video']['description'] = request['description']

    return details


#### VIDEO DOWNLOAD ####

def vid_download(video, dl_location, audio_only):
    """
    Downloads video or audio only if specified

    Arguments:
    video -- video JSON object
    dl_location -- folder to place download
    audio_only -- Boolean indicating audio download only

    Returns:
    None
    """
    if VERBOSE:
        print 'Downloading video --> ' + video['video']['video_id'] + ' | ' + 'From page --> ' + video['page']['page_name'] + '-' + video['page']['page_id']

    try:
        ydl_opts = {
            'outtmpl': dl_location + '/%(id)s - %(title)s',
            'quiet': True
        }

        if audio_only:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3'
            }]

        source = video['video']['source']
        with dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([source])

    except BaseException:
        print 'WARNING: Cannot download video --> ' + video['video']['video_id'] + ' from ' + video['page']['page_name']
