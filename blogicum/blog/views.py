from typing import Any, Dict
from datetime import date
from django import http
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.query import QuerySet
from django.forms.models import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    DetailView, ListView, CreateView, UpdateView, DeleteView
)
from django.shortcuts import get_object_or_404, redirect

from .forms import PostForm, UserForm, CommentForm
from .models import Post, Category, Comment


User = get_user_model()


class ProfileListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = 10

    def dispatch(
            self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        self.user = get_object_or_404(User, username=self.kwargs['username'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        if self.request.user.username == self.kwargs['username']:
            return Post.objects.select_related('author').filter(
                author__username=self.kwargs['username']
            ).annotate(
                comment_count=Count('comments')
            ).order_by('-pub_date')
        else:
            return Post.objects.select_related('author').filter(
                author__username=self.kwargs['username'],
                pub_date__lte=date.today()
            ).order_by('-pub_date')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['profile'] = self.user
        return context


# class ProfileDetailView(DetailView):
#     model = User
#     template_name = 'blog/profile.html'
#     slug_field = 'username'
#     slug_url_kwarg = 'username'

#     def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
#         context = super().get_context_data(**kwargs)
#         context['profile'] = self.get_object()
#         context['user'] = self.request.user
#         paginator = Paginator(
#             Post.objects.select_related('author')
#             .filter(author__username=self.get_object())
#             .order_by('-pub_date'), 10
#         )
#         page_number = self.request.GET.get('page')
#         context['page_obj'] = paginator.get_page(page_number)
#         return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'blog/user.html'

    def get_success_url(self) -> str:
        return reverse('blog:profile', kwargs={'username': self.request.user})

    def get_object(self):
        return self.request.user


def get_published_posts():
    return Post.objects.select_related(
        'location',
        'category',
        'author'
    ).filter(
        pub_date__lte=date.today(),
        is_published=True,
        category__is_published=True
    )


class PostListView(ListView):
    model = Post
    ordering = '-pub_date'
    paginate_by = 10
    queryset = get_published_posts().annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')
    template_name = 'blog/index.html'


class PostValidMixin:
    def form_valid(self, form):
        form.instance.author = self.request.user
        if not form.instance.pub_date:
            form.instance.pub_date = date.today()
        return super().form_valid(form)


class PostCreateView(PostValidMixin, LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self) -> str:
        return reverse('blog:profile', args=[self.request.user.username])


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = (self.object.comments.select_related('author'))
        return context


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def dispatch(
            self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        self.post = get_object_or_404(Post, pk=self.kwargs['pk'])
        if self.request.user != self.post.author:
            raise PermissionDenied
        if not self.request.user.is_authenticated:
            return redirect(
                'blog:post_detail', kwargs={'pk': self.kwargs['pk']}
            )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self) -> str:
        return reverse_lazy(
            'blog:post_detail', kwargs={'pk': self.kwargs['pk']}
        )


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    form_class = PostForm

    def dispatch(
            self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        instance = get_object_or_404(Post, pk=kwargs['pk'])
        if instance.author != request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CommentCreateView(LoginRequiredMixin, CreateView):
    post_object = None
    model = Comment
    form_class = CommentForm

    def dispatch(
            self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        self.post_object = get_object_or_404(Post, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.author = self.request.user
        form.instance.post = self.post_object
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('blog:post_detail', kwargs={'pk': self.post_object.pk})


class CommentMixin:
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'    

    def dispatch(self, request, *args, **kwargs):
        # get_object_or_404(self.model, pk=kwargs['comment_id'], author=request.user)
        instance = get_object_or_404(Post, pk=kwargs['comment_id'])
        if instance.author != request.user:
            return redirect('blog:index')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'pk': self.kwargs['post_id']})


class CommentUpdateView(CommentMixin, LoginRequiredMixin, UpdateView):
    ...


class CommentDeleteView(CommentMixin, LoginRequiredMixin, DeleteView):
    ...


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'blog/category.html'
    paginate_by = 10
    slug_url_kwarg = 'category_slug'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['category'] = self.get_object()
        paginator = Paginator(
            Post.objects.filter(
                category__slug=self.kwargs['category_slug'],
                is_published=True,
                pub_date__lte=date.today()
            ).annotate(
                comment_count=Count('comments')
            ).order_by('-pub_date'),
            10
        )
        page_number = self.request.GET.get('page')
        context['page_obj'] = paginator.get_page(page_number)
        return context
