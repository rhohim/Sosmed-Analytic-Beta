from flask import Flask, redirect, request, jsonify, render_template, url_for, session, Response, flash

app=Flask(__name__)

## instagram libraries
import instaloader
import pandas as pd
from instaloader import Instaloader, Profile
import re
from argparse import ArgumentParser
from sqlite3 import OperationalError, connect
from platform import system
from glob import glob
from os.path import expanduser

from sklearn.datasets import load_boston
import urllib
import os, fnmatch
import json
import shutil

insta = instaloader.Instaloader()
loader = Instaloader(dirname_pattern='static/{target}')

MAX_DAYS = 50 

LIKES_WEIGHT = 1
COMMENTS_WEIGHT = 1
NUM_FOLLOWERS_WEIGHT = 1
NUM_POSTS_WEIGHT = 1
NUM_POSTS = 10

try:
    from instaloader import ConnectionException, Instaloader
except ModuleNotFoundError:
    raise SystemExit("Instaloader not found.\n  pip install [--user] instaloader")

def truncate(num):
    return re.sub(r'^(\d+\.\d{,2})\d*$',r'\1',str(num))

# def send_get_request( url, params, extra_headers=None):
#         url = build_get_url(url, params)
#         did = ''.join(random.choice(string.digits) for num in range(19))
#         url = build_get_url(url, {did_key: did}, append=True)
#         signature = tiktok_browser.fetch_auth_params(url, language=language)
#         url = build_get_url(url, {signature_key: str(signature)}, append=True)
#         if extra_headers is None:
#             headers = header
#         else:
#             headers = {}
#             for key, val in extra_headers.items():
#                 headers[key] = val
#             for key, val in headers.items():
#                 headers[key] = val
#         data = get_req_json(url, params=None, headers=headers)
#         return data



def get_cookiefile():
    default_cookiefile = {
        "Windows": "cookies.sqlite",
        "Darwin": "cookies.sqlite",
    }.get(system(), "~/.mozilla/firefox/*/cookies.sqlite")
    print(default_cookiefile)
    cookiefiles = glob(expanduser(default_cookiefile))
    print(cookiefiles)
    if not cookiefiles:
        raise SystemExit("No Firefox cookies.sqlite file found. Use -c COOKIEFILE.")
    return cookiefiles[0]


def import_session(cookiefile, sessionfile):
    print("Using cookies from {}.".format(cookiefile))
    conn = connect(f"file:{cookiefile}?immutable=1", uri=True)
    try:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE baseDomain='instagram.com'"
        )
    except OperationalError:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
        )
    instaloader = Instaloader(max_connection_attempts=1)
    instaloader.context._session.cookies.update(cookie_data)
    username = instaloader.test_login()
    if not username:
        raise SystemExit("Not logged in. Are you logged in successfully in Firefox?")
    print("Imported session cookie for {}.".format(username))
    instaloader.context.username = username
    instaloader.save_session_to_file(sessionfile)

if __name__ == "__main__":
    p = ArgumentParser()
    p.add_argument("-c", "--cookiefile")
    p.add_argument("-f", "--sessionfile")
    args = p.parse_args()
    try:
        import_session(args.cookiefile or get_cookiefile(), args.sessionfile)
    except (ConnectionException, OperationalError) as e:
        raise SystemExit("Cookie import failed: {}".format(e))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login.html')
def login():
    return render_template('login.html')

@app.route('/index.html')
def home():
    return render_template('index.html')

#for instagram
@app.route('/ig', methods = ["POST","GET"])
def ig():
    
    user = str(request.form.get("fname"))
    print(user)
    try:
        profile = instaloader.Profile.from_username(loader.context, user)
    except:
        print("errrorrrrr")
        flash("account not found or this account is private!")
        return redirect('/index.html')
    profile = instaloader.Profile.from_username(loader.context, user)
    # count = 0
    posts = profile.get_posts()
    num_followers = profile.followers
    total_num_likes = 0
    total_num_comments = 0
    total_num_posts = 0
    valueA = []
    truncA = 0
    i = 0
    for post in profile.get_posts():
        total_num_likes += post.likes
        total_num_comments += post.comments
        total_num_posts += 1
        
        engagement = float(total_num_likes + total_num_comments) / (num_followers * total_num_posts)
        valueA.append(engagement * 100)
        
        #get profile picture
        urllib.request.urlretrieve(profile.get_profile_pic_url(), "G:/CrevHim/Code/software/Social-Media-Analytics-main/static/Profile/pp2.jpg")
        picfolder = os.path.join('static', 'Profile')
        app.config['upload'] = picfolder
        Profile_picture = os.path.join(app.config['upload'], 'pp2.jpg')
        
        
        if i == 11:
            truncA = sum(valueA)/12
            data_ig = (
                ("Username:", profile.full_name),
                ("Verified?:", profile.is_verified),
                ("Followers:", profile.followers),
                ("Media count:", profile.mediacount),
                ("Engagement rate:", ("%.1f" % truncA) + "%"),
                ("Avg likes per post:", int(total_num_likes / total_num_posts)),
                ("Bio:", profile.biography),
                ("External Url:", profile.external_url)
            )

            break
        i += 1
        #data_ig has information about overall instagram account 
        #(username, verified, followers, total post, engagement, evg like, bio, url ) 
    try:
        print(data_ig)
    except:
        print("Private")
        flash("account not found or this account is private!")
        return redirect('/index.html')     
    datatab, show_data = (pd.DataFrame(),)*2
    datajson = []
    i = 0
    TARGET = "post"
    shutil.rmtree("G:/CrevHim/Code/software/Social-Media-Analytics-main/static/post")
    
    for post in (posts):
        loader.download_post(post, target=TARGET)
        datatab = datatab.append({
        "Caption": post.caption,
        "Link": "https://instagram.com/p/" + post.shortcode,
        "Dates": post.date,
        "Likes": post.likes,
        "Comments": post.comments,
        "Views": post.video_view_count
        }, ignore_index=True)
        
        item = {"id": i +1}
        item["like"] = post.likes
        item["comment"] = post.comments
        item["link"] = "https://instagram.com/p/" + post.shortcode
        datajson.append(item)
        i += 1
        if i == 12 :
            break
    
    os.chdir(r".\static\post")
    post_data = [f for f in os.listdir('.') if re.match(r'[0-9]+.*\.jpg', f)]
    files_slide = fnmatch.filter(os.listdir(), "*UTC_1.jpg")
    files = fnmatch.filter(os.listdir(), "*UTC.jpg")
    files.extend(files_slide)
    show_post = []
    for i in post_data:
        for e in files:
            if i == e:
                show_post.append(i)
                
    datatab.index = range(1,len(datatab)+1)
    jsonString = json.dumps(datajson)
    jsonFile = open("G:/CrevHim/Code/software/Social-Media-Analytics-main/static/assets/data.json", "w")
    jsonFile.write(jsonString)
    jsonFile.close() 
              
    picfolder_post = os.path.join('static', 'post')
    app.config['upload'] = picfolder_post
    Profile_post = os.path.join(app.config['upload'], show_post[0])
    
    
    
    
        
    return render_template('index.html',
                        usrname=data_ig[0][1],
                        verified=data_ig[1][1],
                        followers=(f"{data_ig[2][1]:,}"),
                        media_count=data_ig[3][1],
                        engagement_ig=data_ig[4][1],
                        avg_like=data_ig[5][1],
                        bio=data_ig[6][1],
                        url=data_ig[7][1],
                        user_image = Profile_picture,
                        
                        post_1 = os.path.join(app.config['upload'], show_post[11]),
                        caption_1 = str(datatab.iloc[0,0]),
                        link_1 = str(datatab.iloc[0,1]),
                        date_1 = str(datatab.iloc[0,2]),
                        like_1 = str(datatab.iloc[0,3]),
                        comment_1 = str(datatab.iloc[0,4]),
                        view_1 = str(datatab.iloc[0,5]),
                        
                        post_2 = os.path.join(app.config['upload'], show_post[10]),
                        caption_2 = str(datatab.iloc[1,0]),
                        link_2 = str(datatab.iloc[1,1]),
                        date_2 = str(datatab.iloc[1,2]),
                        like_2 = str(datatab.iloc[1,3]),
                        comment_2 = str(datatab.iloc[1,4]),
                        view_2 = str(datatab.iloc[1,5]),
                        
                        post_3 = os.path.join(app.config['upload'], show_post[9]),
                        caption_3 = str(datatab.iloc[2,0]),
                        link_3 = str(datatab.iloc[2,1]),
                        date_3 = str(datatab.iloc[2,2]),
                        like_3 = str(datatab.iloc[2,3]),
                        comment_3 = str(datatab.iloc[2,4]),
                        view_3 = str(datatab.iloc[2,5]),
                        
                        post_4 = os.path.join(app.config['upload'], show_post[8]),
                        caption_4 = str(datatab.iloc[3,0]),
                        link_4 = str(datatab.iloc[3,1]),
                        date_4 = str(datatab.iloc[3,2]),
                        like_4 = str(datatab.iloc[3,3]),
                        comment_4 = str(datatab.iloc[3,4]),
                        view_4 = str(datatab.iloc[3,5]),
                        
                        post_5 = os.path.join(app.config['upload'], show_post[7]),
                        caption_5 = str(datatab.iloc[4,0]),
                        link_5 = str(datatab.iloc[4,1]),
                        date_5 = str(datatab.iloc[4,2]),
                        like_5 = str(datatab.iloc[4,3]),
                        comment_5 = str(datatab.iloc[4,4]),
                        view_5 = str(datatab.iloc[4,5]),
                        
                        post_6 = os.path.join(app.config['upload'], show_post[6]),
                        caption_6 = str(datatab.iloc[5,0]),
                        link_6 = str(datatab.iloc[5,1]),
                        date_6 = str(datatab.iloc[5,2]),
                        like_6 = str(datatab.iloc[5,3]),
                        comment_6 = str(datatab.iloc[5,4]),
                        view_6 = str(datatab.iloc[5,5]),
                        
                        post_7 = os.path.join(app.config['upload'], show_post[5]),
                        caption_7 = str(datatab.iloc[6,0]),
                        link_7 = str(datatab.iloc[6,1]),
                        date_7 = str(datatab.iloc[6,2]),
                        like_7 = str(datatab.iloc[6,3]),
                        comment_7 = str(datatab.iloc[6,4]),
                        view_7 = str(datatab.iloc[6,5]),
                        
                        post_8 = os.path.join(app.config['upload'], show_post[4]),
                        caption_8 = str(datatab.iloc[7,0]),
                        link_8 = str(datatab.iloc[7,1]),
                        date_8 = str(datatab.iloc[7,2]),
                        like_8 = str(datatab.iloc[7,3]),
                        comment_8 = str(datatab.iloc[7,4]),
                        view_8 = str(datatab.iloc[7,5]),
                        
                        post_9 = os.path.join(app.config['upload'], show_post[3]),
                        caption_9 = str(datatab.iloc[8,0]),
                        link_9 = str(datatab.iloc[8,1]),
                        date_9 = str(datatab.iloc[8,2]),
                        like_9 = str(datatab.iloc[8,3]),
                        comment_9 = str(datatab.iloc[8,4]),
                        view_9 = str(datatab.iloc[8,5]),
                        
                        post_10 = os.path.join(app.config['upload'], show_post[2]),
                        caption_10 = str(datatab.iloc[9,0]),
                        link_10 = str(datatab.iloc[9,1]),
                        date_10 = str(datatab.iloc[9,2]),
                        like_10 = str(datatab.iloc[9,3]),
                        comment_10 = str(datatab.iloc[9,4]),
                        view_10 = str(datatab.iloc[9,5]),
                        
                        post_11 = os.path.join(app.config['upload'], show_post[1]),
                        caption_11 = str(datatab.iloc[10,0]),
                        link_11 = str(datatab.iloc[10,1]),
                        date_11 = str(datatab.iloc[10,2]),
                        like_11 = str(datatab.iloc[10,3]),
                        comment_11 = str(datatab.iloc[10,4]),
                        view_11 = str(datatab.iloc[10,5]),
                        
                        post_12 = os.path.join(app.config['upload'], show_post[0]),
                        caption_12 = str(datatab.iloc[11,0]),
                        link_12 = str(datatab.iloc[11,1]),
                        date_12 = str(datatab.iloc[11,2]),
                        like_12 = str(datatab.iloc[11,3]),
                        comment_12 = str(datatab.iloc[11,4]),
                        view_12 = str(datatab.iloc[11,5])
                        
                        )
                      



if __name__ == "__main__":
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.debug = True
    app.run(host="0.0.0.0")