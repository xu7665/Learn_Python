import asyncio
from coroweb import get, post
from model import User, Blog, next_id
from aiohttp import web
import json
import time, re, hashlib
from apis import APIError, APIValueError
from config import configs
import logging


COOKIE_NAME = "awesession"
# to name in set_cookie
_COOKIE_KEY = configs.session.secret


def user2cookie(user, max_age):
    expires = str(time.time()+max_age)
    s = "{}-{}-{}-{}".format(user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode("utf-8")).hexdigest()]
    return "-".join(L)


_RE_EMAIL = re.compile(r"^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$")
_RE_SHA1 = re.compile(r"^[0-9a-f]{40}$")


@post("/api/users")
async def api_register_user(*, name, email, passwd):
    if not name or not name.strip():
        raise APIValueError("name")
    if not email or not _RE_SHA1.match(passwd):
        raise APIValueError("email")
    if not passwd and not _RE_SHA1.match(passwd):
        raise APIValueError("password")
    users = await User.findAll(where="email=?", args=[email])
    # check whether the email has been registered
    if len(users) > 0:
        raise APIError("register failed", "email", "Email is already in use")
    uid = next_id()
    sha1_passwd = "{}:{}".format(uid, passwd)
    user = User(id=uid, name=name.strip(), email=email,
                passwd=hashlib.sha1(sha1_passwd.encode("utf-8")).hexdigest(),
                image="http://www.gravatar.com/avatar/{}?d=mm&s=120".format(
                    hashlib.md5(email.encode("utf-8")).hexdigest()))
    await user.save()
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400),
                 max_age=86400, httponly=True)
    user.passwd = "*******"
    r.content_type = "application/json"
    r.body = json.dumps(user, ensure_ascii=False).encode("utf-8")
    return r


@get('/')
async def handler_url_blog(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs,
        'user': request.__user__,
    }


@get('/greeting')
async def handler_url_greeting(*, name, request):
    body = '<h1>aaa: /greeting {}</h1>'.format(name)
    return body


@get('/users')
async def handler_url_users(request):
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }


@get('/register')
def register(request):
    return {
        "__template__": "register.html"
    }


@post('/api/authenticate')
async def authenticate(*, email, passwd):
    if not email:
        raise APIValueError('email', 'Invalid email')
    if not passwd:
        raise APIValueError('password', 'Invalid password')
    logging.info('this is emmmmmmmmmmmmmm {}'.format(email))
    users = await User.findAll(where='email=?', args=[email])
    if len(users) == 0:
        raise APIValueError('email', 'Email does not exist')
    user = users[0]
    sha1 = hashlib.sha1('{}:{}'.format(user.id, passwd).encode('utf-8'))
    # sha1.update(user.id.encode('utf-8'))
    # sha1.update(b':')
    # sha1.update(passwd.encode('utf-8'))
    if sha1.hexdigest() != user.passwd:
        raise APIValueError('password', 'invalid password')
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400),
                 max_age=86400, httponly=True)
    user.passwd = '*******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if float(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '{}-{}-{}-{}'.format(uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = "******"
        return user
    except Exception as e:
        logging.exception(e)
        return None


@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }
