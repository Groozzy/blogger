from django import forms

from .models import Post, User, Comment


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = '__all__'


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        exclude = ('author', 'is_published')
        widgets = {'pub_date': forms.DateInput(attrs={'type': 'date'})}


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ('text',)
