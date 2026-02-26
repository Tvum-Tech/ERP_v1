from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets, mixins
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .models import Project, Area, SubArea
from .serializers import ProjectSerializer, AreaSerializer, SubAreaSerializer
from apps.common.permissions import IsEditorOrReadOnly
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend



class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all().order_by("-created_at")
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["name", "client_name", "project_code"]

    @action(detail=True, methods=["get", "post"])
    def areas(self, request, pk=None):
        project = self.get_object()

        # GET → list areas of project
        if request.method == "GET":
            areas = project.areas.all()
            serializer = AreaSerializer(areas, many=True)
            return Response(serializer.data)

        # POST → create area under project
        serializer = AreaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project=project)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AreaViewSet(ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsEditorOrReadOnly]

    # FIX: must be iterable
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["name", "area_code"]

    @action(detail=True, methods=["get", "post"], url_path="subareas")
    def subareas(self, request, pk=None):
        # pk = area_id
        if request.method == "GET":
            subareas = SubArea.objects.filter(area_id=pk, is_active=True)
            serializer = SubAreaSerializer(subareas, many=True)
            return Response(serializer.data)

        # POST → create subarea under this area
        data = request.data.copy()
        data["area"] = pk
        serializer = SubAreaSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SubAreaViewSet(ModelViewSet):
    queryset = SubArea.objects.all()
    serializer_class = SubAreaSerializer
    permission_classes = [IsEditorOrReadOnly]

    filter_backends = [SearchFilter, DjangoFilterBackend]
    
    def get_queryset(self):
        area_id = self.request.query_params.get("area_id")
        qs = super().get_queryset()
        if area_id:
            qs = qs.filter(area_id=area_id)
        return qs


@api_view(["GET"])
def project_search(request):
    q = request.GET.get("q", "")
    projects = Project.objects.filter(name__icontains=q)[:10]

    data = [
        {
            "id": p.id,
            "name": p.name,
            "code": getattr(p, "code", ""),
            "client": getattr(p, "client_name", ""),
        }
        for p in projects
    ]

    return Response(data) 