from django.shortcuts import render
from django.contrib.auth import authenticate, login
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from .models import *
from .serializers import *
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect, JsonResponse
from django.core import serializers
from rest_framework.exceptions import NotFound
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import exception_handler
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings

def handler404(request, exception):
    raise NotFound(detail="Error 404, page not found", code=404)

def Handler500(request):
    raise NotFound(detail="Error 500, server error", code=500)

#function to customize error messages response to clients
def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        response.data['status'] = response.status_code
        response.data['error'] = True
        if response.status_code == 401:
            response.data['message'] = response.data['detail']
            del response.data['detail']
        elif response.status_code == 405:
            response.data['message'] = response.data['detail']
            del response.data['detail']

    return response


"""
@api_view(['POST'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def CreateChannel(request):

    if request.method == "POST":
        admin = request.user
        name = request.data.get("channel_name", "")
        url = request.data.get("channel_url", "")
        capacity = 1
        channel_type = request.data.get("channel_type", "")
        if not name or not channel_type or not url:
            return JsonResponse({'message': 'Channel name, type and url is required','error':False,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        try:
            chanel = Channel.objects.get(name__iexact=name)
            return JsonResponse({'message': 'Channel name taken already','error':False,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        except Channel.DoesNotExist:
            pass

        if channel_type == 1:
            channel_type = 'private'
        else:
            channel_type = 'public'

        chanel = Channel.objects.create(admin=admin,name=name,url=url,capacity=capacity,channel_type=channel_type)
        chanel.save()

        channeluser = ChannelUsers.objects.create(channel=chanel,user=admin,role='admin')
        channeluser.save()

        data={
            'id': chanel.id,
            'name': chanel.name,
            'url': chanel.url,
        }
        
        return JsonResponse({'message': 'Your channel has been created successfully','data':data,'error':False,'status':status.HTTP_200_OK},status=status.HTTP_200_OK)
"""

"""
Get all channel endpoint, to get all channels a user is on, in the platform.
"""
@api_view(['GET'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def GetAllChannel(request):
    user = CustomUser.objects.get(email=request.user.email)
    chanel = []
    channels = ChannelUsers.objects.filter(user=user)

    if channels:
        for channel in channels:
            chanel.append(channel.channel)
    else:
        return Response({'message': 'success','error':False,'status':status.HTTP_201_CREATED,'data':[]})

    chanel = ChannelSerializer(chanel, many=True)
    return Response({'message': 'success','error':False,'status':status.HTTP_201_CREATED,'data':chanel.data,})


"""
Get Public channel endpoint, to get public channels available around a users location.
"""
@api_view(['GET'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def GetPublicChannel(request):
    user = CustomUser.objects.get(email=request.user.email)
    channels = Channel.objects.filter(country=user.country,state=user.state,channel_type='public')
    channel = ChannelSerializer(channels, many=True)
    return Response({'message': 'success','error':False,'status':status.HTTP_201_CREATED,'data':channel.data,})


"""
Get channel information endpoint, to get information about a channel
"""
@api_view(['GET'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def GetChannelInfo(request, channel_id):
    try:
        chanel = Channel.objects.get(id=channel_id)
        channeluser = ChannelUsers.objects.get(user=request.user,channel=chanel)
    except Channel.DoesNotExist:
        return JsonResponse({'message': 'Channel does not exist','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
    except ChannelUsers.DoesNotExist:
        return JsonResponse({'message': 'You dont have access to this channel','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    channel = ChannelSerializer(chanel)
    return Response({'message': 'success','error':False,'status':status.HTTP_201_CREATED,'data':channel.data,})


"""
Verify channel endpoint, to check if a channel if exists or not in the platform
"""
@api_view(['POST'])
@csrf_exempt
@permission_classes((permissions.AllowAny, ))
def VerifyChannel(request):
    if request.method == "POST":
        name = request.data.get("name", "")

        if not name:
            return JsonResponse({'message': 'Channel name cannot be empty','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                chanel = Channel.objects.get(name__iexact=name)
                return JsonResponse({'message': 'Channel exist','error':False,'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)
            except Channel.DoesNotExist:
                return JsonResponse({'message': 'Channel does not exist','error':False,'status':status.HTTP_200_OK}, status=status.HTTP_200_OK)

"""
Complain endpoint, to get list of complains in a particular channel
also to post complain to a particular user.
"""
@api_view(['POST','GET'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def Complain(request, channel_id):
    if request.method == "POST": 
        title = request.data.get("title", "")
        description = request.data.get("description", "")

        if not title or not description:
            return JsonResponse({'message': 'Title and description are required','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        try:
            chanel = Channel.objects.get(id=channel_id)
            channeluser = ChannelUsers.objects.get(user=request.user,channel=chanel)
        except Channel.DoesNotExist:
            return JsonResponse({'message': 'Channel does not exist','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        except ChannelUsers.DoesNotExist:
            return JsonResponse({'message': 'You dont have access to this channel','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        complain = ChannelComplain.objects.create(title=title,description=description,user=channeluser,Channel=chanel,is_verified=False,is_irrelevant=False,is_solved=False)
        complain.save()
        data = {
            'title': complain.title,
            'description': complain.description,
            'date': complain.updated_at.date(),
            'time': complain.updated_at.time(),
        }
        return Response({'message': 'success','error':False,'status':status.HTTP_200_OK, 'data':data}, status=status.HTTP_200_OK)
    else:
        try:
            chanel = Channel.objects.get(id=channel_id)
            channeluser = ChannelUsers.objects.get(user=request.user,channel=chanel)
        except Channel.DoesNotExist:
            return JsonResponse({'message': 'Channel does not exist','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        except ChannelUsers.DoesNotExist:
            return JsonResponse({'message': 'You dont have access to this channel','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        #send_mail('Test mail', 'Here is the message.', 'admin@voiceout.com', ['mololuwasamuel12@gmail.com'])
        complains = ChannelComplain.objects.filter(Channel=chanel).order_by('created_at')
        data = ComplainSerializer(complains, many=True)
        return Response({'message': 'Success','error':False,'status':status.HTTP_200_OK, 'data':data.data}, status=status.HTTP_200_OK)


"""
Comment endpoint, to get list of complains in a particular channel
also to post complain to a particular user.
"""
@api_view(['POST','GET'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def Comment(request, complain_id):
    if request.method == "POST": 
        description = request.data.get("description", "")
        if not description:
            return JsonResponse({'message': 'Description are required','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        try:
            complain = ChannelComplain.objects.get(id=complain_id)
            channeluser = ChannelUsers.objects.get(user=request.user,channel=complain.Channel)
        except ChannelComplain.DoesNotExist:
            return JsonResponse({'message': 'Complain does not exist','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        except ChannelUsers.DoesNotExist:
            return JsonResponse({'message': 'You dont have access to this channel','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = ChannelComplainComment.objects.create(Complain=complain,user=channeluser,description=description)
        comment.save()

        data = {
            'user': request.user.id,
            'Complain': complain_id,
            'description': description,
            'date': complain.updated_at.date(),
            'time': complain.updated_at.time(),
        }

        return Response({'message': 'Success','error':False,'status':status.HTTP_200_OK, 'data':data}, status=status.HTTP_200_OK)
    elif request.method == "GET":
        try:
            complain = ChannelComplain.objects.get(id=complain_id)
            channeluser = ChannelUsers.objects.get(user=request.user,channel=complain.Channel)
        except ChannelComplain.DoesNotExist:
            return JsonResponse({'message': 'Complain does not exist','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        except ChannelUsers.DoesNotExist:
            return JsonResponse({'message': 'You dont have access to this channel','error':True,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        comments = ChannelComplainComment.objects.filter(Complain=complain)
        comments = CommentSerializer(comments, many=True)
        return Response({'message': 'Success','error':False,'status':status.HTTP_200_OK, 'data':comments.data}, status=status.HTTP_200_OK)

"""
Complain list endpoint, to get list of complains made by a user on every channel
"""
@api_view(['GET'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def ComplainList(request):
    if request.method == "GET":
        user = ChannelUsers.objects.filter(user=request.user)

        if not user:
            return JsonResponse({'message': 'You have not joined any channel','error':False,'status':status.HTTP_200_OK, 'data':[]}, status=status.HTTP_200_OK)
        else:
            data = ChannelComplain.objects.filter(user__user__email=request.user.email)
            data = ComplainSerializer(data, many=True)
            return Response({'message': 'Success','error':False,'status':status.HTTP_200_OK, 'data':data.data}, status=status.HTTP_200_OK)
            
"""
Comment list endpoint, to get list of comments made on a user complains
"""
@api_view(['GET'])
@csrf_exempt
@permission_classes((permissions.IsAuthenticated, ))
def ReplyList(request):
    if request.method == "GET":
        user = ChannelUsers.objects.filter(user=request.user)

        if not user:
            return JsonResponse({'message': 'You have not joined any channel','error':False,'status':status.HTTP_200_OK, 'data':[]}, status=status.HTTP_200_OK)
        else:
            data = ChannelComplainComment.objects.filter(user__user__email=request.user.email)
            return Response({'message': 'Success','error':False,'status':status.HTTP_200_OK, 'data':data}, status=status.HTTP_200_OK)

class ListChannelView(generics.ListAPIView):
    """
    Provides a get method handler.
    """
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = (permissions.IsAuthenticated,)