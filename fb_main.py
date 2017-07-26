import json
import fb_search as fb


if __name__ == '__main__':
    #### SEARCH PARAMETERS ####
    PG_SEARCH_LIMIT = 3
    VIDEO_LIMIT = 10
    QUERY_LIST = []     # Enter list of query requests as strings

    #### DOWNLOAD PARAMETERS ####
    DOWNLOAD_VIDEOS = True
    AUDIO_ONLY = True
    VIDEO_DIRECTORY_NAME = 'video_data'

    open('pg_video.json', 'w').close()
    open('page_verified.json', 'w').close()
    open('page_to_be_verified.json', 'w').close()
    if DOWNLOAD_VIDEOS:
        fb.make_directory(VIDEO_DIRECTORY_NAME)

    page_verified = []
    page_to_be_verified = []
    for query in QUERY_LIST:
        page = fb.select_page(query, PG_SEARCH_LIMIT)
        if page is None:
            continue

        if fb.is_verified_page(page):
            page_verified.append(page)
        else:
            page_to_be_verified.append(page)

    with open('page_verified.json', 'a') as outfile:
        json.dump(page_verified, outfile, indent=4, sort_keys=True)

    with open('page_to_be_verified.json', 'a') as outfile:
        json.dump(page_to_be_verified, outfile, indent=4, sort_keys=True)

    valid_video = []
    for page in page_verified:
        videos = fb.search_page_videos(page['page_id'], VIDEO_LIMIT)
        valid_video.extend(videos)

    with open('pg_video.json', 'a') as outfile:
        json.dump(valid_video, outfile, indent=4, sort_keys=True)
        print 'Found ' + str(len(valid_video)) + ' related resources.'

    if DOWNLOAD_VIDEOS:
        for video in valid_video:
            page = video['page']['page_name'] + '-' + video['page']['page_id']
            fb.vid_download(video, VIDEO_DIRECTORY_NAME + '/' + page, audio_only=AUDIO_ONLY)
