import json
import uuid
import requests

from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings

from urllib.parse import urlencode

from .models import User

# Create your views here.

def login(request):

    base = "https://github.com/login/oauth/authorize"

    parameters = {}
    parameters['client_id'] = settings.GITHUB_CLIENT_ID
    parameters['redirect_uri'] = settings.SITE_URL + "/get_code"
    parameters['scope'] = 'repo:status'
    parameters['state'] = '1290jdjwoqj'

    url = base + '?' + urlencode(parameters)

    return redirect(url)

def get_code(request):

    code = request.GET.get('code')
    state = request.GET.get('state')

    # TODO - should check state

    # Get access token

    base = "https://github.com/login/oauth/access_token"

    parameters = {}
    parameters['client_id'] = settings.GITHUB_CLIENT_ID
    parameters['client_secret'] = settings.GITHUB_CLIENT_SECRET
    parameters['code'] = code
    parameters['redirect_uri'] = settings.SITE_URL + "/login-success"

    response = requests.post(base,
                             parameters,
                             headers={'Accept':'application/json'}).json()

    access_token = response['access_token']

    # Find current user

    parameters = {}
    parameters['access_token'] = access_token

    base = "https://api.github.com/user"

    response = requests.get(base, headers={'Authorization':'token ' + access_token}).json()

    login = response['login']

    # Create user in database

    try:
        user = User.objects.get(username=login)
    except User.DoesNotExist:
        user = User(username=login, access_token=access_token, hook_id=str(uuid.uuid1()))
        user.save()

    # Create hook url
    hook_url = settings.SITE_URL + "/hook/{hook_id}/".format(hook_id=user.hook_id)

    # Return instructions on setting up webhook
    return HttpResponse("Authorization successful! Now you can add the following "
                        "webhook on any repository you have push access to in order "
                        "to enable the multi-status functionality: {url}".format(url=hook_url))

def hook(response, hook_id):

    # If call is not from GitHub, we should just ignore
    if not 'HTTP_X_GITHUB_EVENT' in response.META:
        return HttpResponse('')

    # We only listen to status updates
    if response.META['HTTP_X_GITHUB_EVENT'] != 'status':
        return HttpResponse('')

    response = json.loads(response.body.decode('utf-8'))

    # We avoid any circular triggering
    if response.get('context') == 'statusupdater':
        return HttpResponse("won't comment on my own updates")

    # Get the SHA of the commit that triggered the change
    sha = response.get('sha')

    name = response.get('name')

    owner, repo = name.split('/')

    base = 'https://api.github.com/repos/{owner}/{repo}/statuses/{sha}'.format(owner=owner, repo=repo, sha=sha)

    user = User.objects.get(hook_id=hook_id)

    parameters = {}
    parameters['state'] = 'success'
    parameters['target_url'] = 'http://astrofrog.pythonanywhere.com'
    parameters['description'] = "This is a test of the multistatus webapp"
    parameters['context'] = 'statusupdater'

    parameters = json.dumps(parameters)

    import requests
    response = requests.post(base, parameters,
                             headers={'Authorization':'token ' + user.access_token})

    return HttpResponse("Using user=" + user.username + " and hook_id=" + hook_id)
