# market/views.py
from rest_framework import generics, filters, permissions, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Produce
from .serializers import ProductSerializer

class ProductListView(generics.ListAPIView):
    """
    List all products (public access)
    """
    permission_classes = [permissions.AllowAny]
    queryset = Produce.objects.filter(available=True).select_related('farmer')
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'farmer__name', 'location']

class ProductCreateView(generics.CreateAPIView):
    """
    Create a new product (farmers only)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer
    queryset = Produce.objects.all()

    def perform_create(self, serializer):
        # Check if user is a farmer
        if self.request.user.user_type != 'farmer':
            return Response(
                {"error": "Only farmers can create products"},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save(farmer=self.request.user)

class ProductRetrieveView(generics.RetrieveAPIView):
    """
    Retrieve a single product by its ID
    """
    permission_classes = [permissions.AllowAny]
    queryset = Produce.objects.filter(available=True).select_related('farmer')
    serializer_class = ProductSerializer
    lookup_field = 'pk'