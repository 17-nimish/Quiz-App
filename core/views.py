from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from .models import Category, Quiz, Question, Option, Attempt, Answer
import csv
import random
from django.http import HttpResponse
from io import TextIOWrapper

# ✅ Home page → show categories
def home(request):
    categories = Category.objects.all()
    return render(request, 'core/home.html', {'categories': categories})


# ✅ Register new user
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        # Validation
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('register')

        # Save user
        User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )
        messages.success(request, "Account created successfully. Please login.")
        return redirect('login')

    return render(request, 'core/register.html')


# ✅ Login
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome {username}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')

    return render(request, 'core/login.html')


# ✅ Logout
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# ✅ Quizzes by Category
def category_quizzes(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    quizzes = Quiz.objects.filter(category=category)
    return render(request, 'core/quizzes_by_category.html', {
        'category': category,
        'quizzes': quizzes
    })


# ✅ Start Quiz
@login_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    # check if quiz is active
    if quiz.status != 'active':
        messages.warning(request, "This quiz is not currently active.")
        return redirect('category_quizzes', category=quiz.category.id)

    # randomize questions
    questions = list(quiz.question_set.all().order_by('?'))

    # Initialize quiz session
    request.session['quiz_id'] = quiz_id
    request.session['question_index'] = 0
    request.session['score'] = 0
    request.session['answers'] = {}
    request.session['question_order'] = [q.id for q in questions]  # save random order

    return redirect('attempt_quiz')


# ✅ Attempt Quiz (one question at a time)
@login_required
def attempt_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    request.session['quiz_id'] = quiz.id

    # Get or initialize session state
    question_index = request.session.get('question_index', 0)
    question_order = request.session.get('question_order')

    if not question_order or request.session.get('quiz_id') != quiz_id:
        # First time starting this quiz → randomize only this quiz's questions
        question_order = list(
            quiz.question_set.values_list('id', flat=True)  # ✅ only this quiz
        )
        random.shuffle(question_order)
        request.session['question_order'] = question_order
        request.session['question_index'] = 0
        request.session['score'] = 0
        request.session['answers'] = {}

    # ✅ Only pull questions that belong to this quiz
    questions = Question.objects.filter(id__in=question_order, quiz=quiz)

    # If quiz is finished → go to result page
    if question_index >= len(questions):
        return redirect('quiz_result')

    current_question = get_object_or_404(Question, id=question_order[question_index], quiz=quiz)
    options = current_question.options.all()

    if request.method == 'POST':
        selected_option_id = request.POST.get('option')
        if selected_option_id:
            selected_option = get_object_or_404(Option, id=selected_option_id, question=current_question)

            # Store answer
            answers = request.session.get('answers', {})
            answers[str(current_question.id)] = selected_option.id
            request.session['answers'] = answers

            # Update score
            if selected_option.is_correct:
                request.session['score'] += 1

            # Move to next question
            request.session['question_index'] += 1
            return redirect('attempt_quiz', quiz_id=quiz_id)

    return render(request, 'core/quiz_attempt.html', {
        'quiz': quiz,
        'question': current_question,
        'options': options,
        'question_number': question_index + 1,
        'total_questions': len(question_order),
    })


# ✅ Quiz Result
@login_required
def quiz_result(request):
    score = request.session.get('score', 0)
    quiz_id = request.session.get('quiz_id')
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    total_questions = quiz.question_set.count()
    answers = request.session.get('answers', {})

    # Save attempt
    attempt = Attempt.objects.create(
        user=request.user,
        quiz=quiz,
        score=score,
        total=total_questions,
    )

    # Save each answer
    for qid, oid in answers.items():
        question = get_object_or_404(Question, pk=qid)
        option = get_object_or_404(Option, pk=oid)
        Answer.objects.create(
            attempt=attempt,
            question=question,
            selected_option=option
        )

    # Clear session after saving
    for key in ['score', 'quiz_id', 'question_index', 'answers', 'question_order']:
        request.session.pop(key, None)

    return render(request, 'core/quiz_result.html', {
        'score': score,
        'total_questions': total_questions,
        'quiz': quiz
    })


# ✅ User’s Attempt History
@login_required
def my_attempts(request):
    attempts = Attempt.objects.filter(user=request.user).order_by('-completed_at')
    return render(request, 'core/my_attempts.html', {'attempts': attempts})


# ✅ Admin Dashboard
@staff_member_required
def admin_dashboard(request):
    context = {
        'total_users': User.objects.count(),
        'total_quizzes': Quiz.objects.count(),
        'total_attempts': Attempt.objects.count(),
        'top_quizzes': Quiz.objects.annotate(attempts=Count('attempt')).order_by('-attempts')[:5],
    }
    return render(request, 'core/admin_dashboard.html', context)


@staff_member_required
def download_users_csv(request):
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Username', 'Email', 'Date Joined', 'Last Login'])

    users = User.objects.all().values_list('id', 'username', 'email', 'date_joined', 'last_login')
    for user in users:
        writer.writerow(user)

    return response


@staff_member_required
def admin_manage_quizzes(request):
    quizzes = Quiz.objects.all()
    return render(request, 'core/admin_quizzes.html', {'quizzes': quizzes})


@staff_member_required
def admin_add_quiz(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        status = request.POST.get('status')
        category = get_object_or_404(Category, id=category_id)
        Quiz.objects.create(title=title, category=category, status=status)
        messages.success(request, "Quiz added successfully.")
        return redirect('admin_manage_quizzes')
    return render(request, 'core/admin_add_quiz.html', {'categories': categories})


@staff_member_required
def admin_edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    categories = Category.objects.all()
    if request.method == 'POST':
        quiz.title = request.POST.get('title')
        category_id = request.POST.get('category')
        quiz.category = get_object_or_404(Category, id=category_id)
        quiz.status = request.POST.get('status')
        quiz.save()
        messages.success(request, "Quiz updated successfully.")
        return redirect('admin_manage_quizzes')
    return render(request, 'core/admin_edit_quiz.html', {'quiz': quiz, 'categories': categories})


@staff_member_required
def admin_delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.delete()
    messages.success(request, "Quiz deleted.")
    return redirect('admin_manage_quizzes')


@staff_member_required
def upload_quizzes_csv(request):
    if request.method == 'POST':
        csv_file = request.FILES['csv_file']
        file_data = TextIOWrapper(csv_file.file, encoding='utf-8')
        reader = csv.DictReader(file_data)
        for row in reader:
            category_name = row['category']
            category, _ = Category.objects.get_or_create(name=category_name)
            Quiz.objects.create(
                title=row['title'],
                category=category,
                status=row.get('status', 'active')
            )
        messages.success(request, "Quizzes uploaded successfully.")
        return redirect('admin_manage_quizzes')
    return render(request, 'core/admin_upload_quizzes.html')
