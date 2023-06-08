from typing import Any, Dict
from datetime import date
from django.http import Http404
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.query import QuerySet
from django.forms.models import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    DetailView,
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.shortcuts import get_object_or_404, redirect

from .forms import PostForm, UserForm, CommentForm
from .models import Post, Category, Comment


User = get_user_model()


class ProfileListView(ListView):
    model = Post
    template_name = "blog/profile.html"
    paginate_by = 10

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        self.user = get_object_or_404(User, username=self.kwargs["username"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        queryset = (
            Post.objects.select_related("author")
            .filter(author__username=self.kwargs["username"])
            .order_by("-pub_date")
        )
        if self.request.user.username == self.kwargs["username"]:
            return queryset.annotate(comment_count=Count("comments"))
        else:
            return queryset.filter(pub_date__lte=date.today())

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["profile"] = self.user
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = "blog/user.html"

    def get_success_url(self) -> str:
        return reverse(
            "blog:profile", kwargs={"username": self.request.user.username}
        )

    def get_object(self):
        return self.request.user


def get_published_posts():
    return Post.objects.select_related(
        "location", "category", "author"
    ).filter(
        pub_date__lte=date.today(),
        is_published=True,
        category__is_published=True,
    )


class PostListView(ListView):
    model = Post
    ordering = "-pub_date"
    paginate_by = 10
    queryset = (
        get_published_posts()
        .annotate(comment_count=Count("comments"))
        .order_by("-pub_date")
    )
    template_name = "blog/index.html"


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse("blog:profile", args=[self.request.user.username])


class PostDetailView(DetailView):
    model = Post
    template_name = "blog/detail.html"
    pk_url_kwarg = "post_id"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["form"] = CommentForm()
        context["comments"] = self.object.comments.select_related("author")
        return context


class UpdateDeleteMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()

        if isinstance(obj, Post):
            pk = obj.pk
        elif isinstance(obj, Comment):
            pk = obj.post.pk
        else:
            raise Http404

        if obj.author != self.request.user:
            return redirect("blog:post_detail", pk)

        return super().dispatch(request, *args, **kwargs)


class PostUpdateView(UpdateDeleteMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"

    def get_success_url(self) -> str:
        return reverse_lazy(
            "blog:post_detail", kwargs={"post_id": self.kwargs["post_id"]}
        )


class PostDeleteView(UpdateDeleteMixin, DeleteView):
    model = Post
    form_class = PostForm

    def get_success_url(self) -> str:
        return reverse_lazy("blog:index")


class CommentCreateView(LoginRequiredMixin, CreateView):
    post_object = None
    model = Comment
    form_class = CommentForm
    pk_url_kwarg = "post_id"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        self.post_object = get_object_or_404(Post, pk=kwargs["post_id"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.author = self.request.user
        form.instance.post = self.post_object
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse(
            "blog:post_detail", kwargs={"post_id": self.post_object.pk}
        )


class CommentUpdateView(UpdateDeleteMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def get_success_url(self):
        return reverse(
            "blog:post_detail", kwargs={"post_id": self.kwargs["post_id"]}
        )


class CommentDeleteView(UpdateDeleteMixin, DeleteView):
    model = Comment
    form_class = CommentForm
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def get_success_url(self):
        return reverse(
            "blog:post_detail", kwargs={"post_id": self.kwargs["post_id"]}
        )


class CategoryDetailView(DetailView):
    model = Category
    template_name = "blog/category.html"
    paginate_by = 10
    slug_url_kwarg = "category_slug"

    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        get_object_or_404(
            Category, slug=kwargs["category_slug"], is_published=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["category"] = self.get_object()
        paginator = Paginator(
            get_published_posts()
            .annotate(comment_count=Count("comments"))
            .order_by("-pub_date"),
            10,
        )
        page_number = self.request.GET.get("page")
        context["page_obj"] = paginator.get_page(page_number)
        return context
