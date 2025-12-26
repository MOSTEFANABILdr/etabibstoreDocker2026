from rocketchat_API.rocketchat import RocketChat

from core.enums import RocketChatGroup, RocketChatGroupId
from etabibWebsite import settings

rocket = None


def fetchRcUser(username):
    global rocket
    if not rocket:
        rocket = RocketChat(settings.ROCKETCHAT_ADMIN_USERNAME, settings.ROCKETCHAT_ADMIN_PASSWORD,
                            server_url=settings.ROCKET_CHAT_SERVER)
    r = rocket.users_info(username=username)
    return r.json()


def loginRcUser(username, password=settings.ROCKETCHAT_DEFAULT_USER_PASSWORD):
    global rocket
    if not rocket:
        rocket = RocketChat(settings.ROCKETCHAT_ADMIN_USERNAME, settings.ROCKETCHAT_ADMIN_PASSWORD,
                            server_url=settings.ROCKET_CHAT_SERVER)
    r = rocket.login(user=username, password=password)
    return r.json()


def createRcUser(username, name, email, password=settings.ROCKETCHAT_DEFAULT_USER_PASSWORD):
    global rocket
    if not rocket:
        rocket = RocketChat(settings.ROCKETCHAT_ADMIN_USERNAME, settings.ROCKETCHAT_ADMIN_PASSWORD,
                            server_url=settings.ROCKET_CHAT_SERVER)
    r = rocket.users_create(email, name, password, username)
    return r.json()


def createOrLoginRcUser(username, name, email, password=settings.ROCKETCHAT_DEFAULT_USER_PASSWORD):
    try:
        data = fetchRcUser(username)
        if "status" in data:
            print("error")
            if data["status"] == "error":
                raise Exception("")
        return loginRcUser(username, password)
    except Exception as e:
        # User does not exist, creating user
        user = createRcUser(username, name, email, password)
        # Perfom login
    return loginRcUser(username, password)


def createRcGroups():
    global rocket
    if not rocket:
        rocket = RocketChat(settings.ROCKETCHAT_ADMIN_USERNAME, settings.ROCKETCHAT_ADMIN_PASSWORD,
                            server_url=settings.ROCKET_CHAT_SERVER)
    rocket.groups_create(RocketChatGroup.SALES_TEAM.value)
    rocket.groups_create(RocketChatGroup.TECHNICAL_TEAM.value)
    rocket.groups_create(RocketChatGroup.ALL_MEMBERS.value)


def joinRcGroups(user, rocketChatUserId):
    global rocket
    if not rocket:
        rocket = RocketChat(settings.ROCKETCHAT_ADMIN_USERNAME, settings.ROCKETCHAT_ADMIN_PASSWORD,
                            server_url=settings.ROCKET_CHAT_SERVER)
    # check if the user has entered to the specific channels before
    jsn = rocket.users_info(user_id=rocketChatUserId, fields='{"userRooms": 1}').json()
    if jsn["success"] == True:
        roomIds = []
        for room in jsn["user"]["rooms"]:
            roomIds.append(room["rid"])
        if RocketChatGroupId.TECHNICAL_TEAM.value not in roomIds:
            rocket.groups_invite(RocketChatGroupId.TECHNICAL_TEAM.value, rocketChatUserId)
        if RocketChatGroupId.SALES_TEAM.value not in roomIds:
            rocket.groups_invite(RocketChatGroupId.SALES_TEAM.value, rocketChatUserId)
        if RocketChatGroupId.ALL_MEMBERS.value not in roomIds:
            rocket.groups_invite(RocketChatGroupId.ALL_MEMBERS.value, rocketChatUserId)


def setRcUserPreferences(rocketChatUserId, data={}):
    global rocket
    if not rocket:
        rocket = RocketChat(settings.ROCKETCHAT_ADMIN_USERNAME, settings.ROCKETCHAT_ADMIN_PASSWORD,
                            server_url=settings.ROCKET_CHAT_SERVER)
    r = rocket.users_set_preferences(user_id=rocketChatUserId, data=data)
    print(r.json())
