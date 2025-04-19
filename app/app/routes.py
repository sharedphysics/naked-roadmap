from app import app, db, login
from app.forms import LoginForm, RegistrationForm, CreateProject, CreateGoal, CreateSprint, CommentForm
from app.models import User, Project, Goal, Sprint, SprintProjectMap, Comment, Changelog
import sqlalchemy as sa
from flask import Flask, render_template, request, url_for, flash, redirect, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.exceptions import abort
from urllib.parse import urlsplit
from config import Config
from datetime import datetime
from flask_wtf.csrf import generate_csrf
from . import utils
from .utils import ALLOWED_TAGS, ALLOWED_ATTRIBUTES, clean_html
import bleach
from sqlalchemy import func

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())

@app.route('/')
@app.route('/index')
@login_required # If you want to toggle someone forced to log in to see roadmap, you can use this. 
def index():
    # if not current_user.is_verified:
    #     return redirect(url_for("auth.verify"))
    projects = (
        Project.query
        .order_by(Project.created.desc())
        .limit(5)
    )
    goals = (
        db.session.query(
            Goal,
            func.count(Project.id).label('active_project_count')
        )
        .outerjoin(Project, (Project.objective_id == Goal.id) & (Project.status == 'Active'))
        .group_by(Goal.id)
        .order_by(Goal.created.desc())
        .all()
    )
    sprints = (
        Sprint.query
        .order_by(Sprint.date_start.desc())
        .all()
    )
    sprintlog = (
        SprintProjectMap.query
        .order_by(SprintProjectMap.order.asc())
        .all()
    )
    comments = (
        Comment.query
        .order_by(Comment.created_at.desc())
        .limit(5)
    )
    changes = (
        Changelog.query
        .order_by(Changelog.timestamp.desc())
        .limit(5)
    )
    today = datetime.now()
    return render_template('index.html', title='Home', projects=projects, goals=goals, config=Config, sprints=sprints, sprintlog=sprintlog, datetime=datetime, today=today, comments=comments, changes=changes)
    
@app.route('/project/<int:project_id>')
def project(project_id):
    project = Project.query.filter_by(id=project_id).first_or_404()
    
    # Get comments for this project
    comments = Comment.query.filter_by(project_id=project_id).order_by(Comment.created_at.desc()).all()
    
    # Get changelog entries for this project
    changelogs = Changelog.query.filter_by(project_id=project_id).order_by(Changelog.timestamp.desc()).all()
    
    # Get cycle commitment entries for this project
    cycles = SprintProjectMap.query.filter_by(project_id=project_id).order_by(SprintProjectMap.added.desc()).all()
    
    active_goals = Goal.query.filter_by(status='Active').all()
    
    # Initialize comment form
    form = CommentForm()
    
    return render_template('project.html', project=project, comments=comments, changelogs=changelogs, form=form, cycles=cycles, active_goals=active_goals)
    
@app.route('/project/<int:project_id>/edit/', methods=('GET', 'POST'))
@login_required
def edit_project(project_id):
    project = Project.query.filter_by(id=project_id).first_or_404()
    
    # Check if user has permission to edit the project
    if not current_user.can_edit_project(project):
        flash('You do not have permission to edit this project.', 'error')
        return redirect(url_for('index'))
    
    form = CreateProject()
    
    if request.method == 'POST':
        # Check for CSRF token validity
        if not form.validate_on_submit():
            if request.is_xhr:  # For AJAX requests (autosave)
                return jsonify({'success': False, 'message': 'CSRF validation failed'})
            flash('Form validation failed. Please try again.', 'error')
            return render_template('edit.html', project=project, form=form)
        
        # Track what changed
        changes = []
        if project.name != form.name.data:
            changes.append(f"Name: '{project.name}' → '{form.name.data}'")
        if project.dri != form.dri.data:
            changes.append(f"DRI: '{project.dri}' → '{form.dri.data}'")
        if project.team != form.team.data:
            changes.append(f"Team: '{project.team}' → '{form.team.data}'")
        
        # For text fields, just note that they were updated (to avoid storing large diffs)
        if project.context != form.context.data:
            changes.append(f"Context updated")
        if project.why != form.why.data:
            changes.append(f"Why updated")
        if project.requirements != form.requirements.data:
            changes.append(f"Requirements updated")
        if project.launch != form.launch.data:
            changes.append(f"Launch updated")
        
        # Sanitize HTML input to prevent XSS attacks
        sanitized_data = {
            'name': bleach.clean(form.name.data, strip=True),
            'dri': bleach.clean(form.dri.data, strip=True),
            'team': bleach.clean(form.team.data, strip=True),
            'context': clean_html(form.context.data),
            'why': clean_html(form.why.data),
            'requirements': clean_html(form.requirements.data),
            'launch': clean_html(form.launch.data)
        }
        
        # Check if this is an autosave request
        is_autosave = request.form.get('autosave') == 'true'
        
        # Update the project
        Project.query.filter_by(id=project_id).update(sanitized_data)
        
        # Create changelog entry if changes were made and not an autosave
        if changes and not is_autosave:
            change_content = ", ".join(changes)
            changelog = Changelog(
                change_type='edit',
                content=change_content,
                project_id=project_id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(changelog)
        
        db.session.commit()
        
        # For AJAX requests (autosave)
        if request.is_xhr:
            return jsonify({'success': True, 'message': 'Changes saved'})
        
        if not is_autosave:
            flash('Project updated successfully!', 'success')
            return redirect(url_for('project', project_id=project_id))
    
    # Populate form with existing values if it's a GET request
    if request.method == 'GET':
        form.name.data = project.name
        form.dri.data = project.dri
        form.team.data = project.team
        form.context.data = project.context
        form.why.data = project.why
        form.requirements.data = project.requirements
        form.launch.data = project.launch

    return render_template('edit.html', project=project, form=form)
    
@app.route('/project/<int:project_id>/update_type', methods=['POST'])
def update_project_type(project_id):
    if request.method == 'POST':
        data = request.get_json()
        project_type = data.get('type')
        
        if project_type not in ['project', 'task']:
            return jsonify({'error': 'Invalid project type'}), 400
        
        project = Project.query.get_or_404(project_id)
        old_type = project.type if project.type else 'Not set'
        project.type = project_type
        db.session.commit()
        
        try:
            # Create changelog entry using the correct fields from your model
            user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
            
            # Ensure we have a user_id since it's not nullable
            if user_id is None:
                # You might want to use a system user ID or handle this differently
                # depending on your application's requirements
                return jsonify({'success': True, 'type': project_type, 'warning': 'No user detected, changelog not created'})
            
            changelog = Changelog(
                project_id=project_id,
                change_type='edit',  # This is 'change_type' in your model
                content=f'Project type changed from "{old_type}" to "{project_type}"',  # This is 'content' in your model
                user_id=user_id
                # timestamp will be automatically set by the default
            )
            db.session.add(changelog)
            db.session.commit()
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Error creating changelog: {str(e)}")
            # Don't roll back the project change even if changelog fails
        
        return jsonify({'success': True, 'type': project_type})
    
@app.route('/projects/<int:project_id>/associate-objective', methods=['POST'])
@login_required
def associate_objective(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Check for remove association request
    if 'remove_association' in request.form:
        # Get the objective name for the changelog before removing it
        objective_name = project.objective.title if project.objective else "Unknown objective"
        
        # Remove the association
        project.objective_id = None
        project.objective = None
        
        # Create a changelog entry
        changelog = Changelog(
            project_id=project.id,
            user_id=current_user.id,
            change_type='objective_removed',
            content=f"Removed association with objective: {objective_name}"
        )
        db.session.add(changelog)
        db.session.commit()
        
        flash('Objective association removed.', 'success')
        return redirect(url_for('project', project_id=project.id))
    
    # Handle new or updated association
    objective_id = request.form.get('objective_id')
    if objective_id:
        objective = Goal.query.get(objective_id)
        if objective:
            # Check if this is a new association or update
            if project.objective_id != objective.id:
                # Store old objective name for changelog if updating
                old_objective = "None"
                if project.objective:
                    old_objective = project.objective.title
                
                # Update the association
                project.objective_id = objective.id
                project.objective = objective
                
                # Create a changelog entry
                if old_objective == "None":
                    change_type = 'objective_added'
                    content = f"Added association with objective: {objective.title}"
                else:
                    change_type = 'objective_changed'
                    content = f"Changed objective from '{old_objective}' to '{objective.title}'"
                
                changelog = Changelog(
                    project_id=project.id,
                    user_id=current_user.id,
                    change_type=change_type,
                    content=content
                )
                db.session.add(changelog)
                db.session.commit()
                
                flash('Project linked to objective successfully.', 'success')
            else:
                # No change was made
                flash('No changes to objective association.', 'info')
        else:
            flash('Selected objective not found.', 'error')
    else:
        flash('No objective selected.', 'warning')
    
    return redirect(url_for('project', project_id=project.id))

@app.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id).first_or_404()
    # Implement project delete logic here
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('dashboard'))
    
    
@app.route('/create', methods=['GET', 'POST'])
@login_required  # Make sure this is required to track the user
def createProject():
    form = CreateProject()
    if request.method == 'POST':
        projectDetails = Project(
            name=form.name.data,
            dri=form.dri.data,
            team=form.team.data,
            context=form.context.data,
            why=form.why.data,
            requirements=form.requirements.data,
            launch=form.launch.data, 
        )

        db.session.add(projectDetails)
        db.session.flush()  # This gets us the ID of the new project
        
        # Create changelog entry
        changelog = Changelog(
            change_type='create',
            content=f"Project '{form.name.data}' created",
            project_id=projectDetails.id,
            user_id=current_user.id
        )
        db.session.add(changelog)
        db.session.commit()
        
        flash('Congratulations, project created!')
        return redirect(url_for('index'))
        
    return render_template('create.html', form=form)

@app.route('/project/<int:project_id>/edit/', methods=('GET', 'POST'))
def edit(project_id):
    project = (
        Project.query
        .filter_by(id=project_id)
        .first()
    )
    form = CreateProject()
    if request.method == 'POST':
        Project.query.filter_by(id=project_id).update(dict( 
            name=form.name.data,
            dri=form.dri.data,
            team=form.team.data,
            context=form.context.data,
            why=form.why.data,
            requirements=form.requirements.data,
            launch=form.launch.data
        )
        )
        db.session.commit()
        
        flash('Congratulations, project edited!')
        return redirect(url_for('index'))

    return render_template('edit.html', project=project, form=form)

@app.route('/<int:project_id>/delete', methods=('POST',))
def delete(project_id):
    deleteProject = db.session.query(Project).filter(Project.id==project_id).first()
    db.session.delete(deleteProject)
    db.session.commit()
    # db.session.scalar(Project.query.filter_by(id=project_id).delete())
    flash('Project was successfully deleted!')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)
    
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)
    
    

########################################################
### Managing Projects
########################################################

@app.route('/projects')
@login_required # If you want to toggle someone forced to log in to see roadmap, you can use this. 
def projectspage():
    # if not current_user.is_verified:
    #     return redirect(url_for("auth.verify"))
    projects = (
        Project.query
        .order_by(Project.created.desc())
        .all()
    )
    return render_template('projects.html', title='Projects', projects=projects)
    
    
########################################################
### Managing Objectives
########################################################

@app.route('/goals', methods=['GET', 'POST'])
def createGoal():
    form = CreateGoal()
    if form.validate_on_submit():
        new_goal = Goal(
            title=form.title.data,
            details=form.details.data,
            requested_by=form.requested_by.data,
            user_id=current_user.id
        )
        db.session.add(new_goal)
        db.session.commit()
        flash('Goal created successfully.')
        return redirect(url_for('createGoal'))

    goals = Goal.query.order_by(Goal.created.desc()).all()
    return render_template('objectives.html', form=form, goals=goals)


@app.route('/goals/edit', methods=['POST'])
@login_required
def editGoal():
    goal_id = request.form.get('goal_id')
    goal = Goal.query.get(goal_id)
    if goal:
        goal.title = request.form.get('title')
        goal.details = request.form.get('details')
        goal.requested_by = request.form.get('requested_by')
        db.session.commit()
        flash('Goal updated successfully.')
    else:
        flash('Goal not found.')
    return redirect(url_for('createGoal'))
    
    
########################################################
### Managing Sprints
########################################################

@app.route('/sprint', methods=['GET', 'POST'])
def createSprint():
    form = CreateSprint()
    
    try:
        if request.method == 'POST':
            sprintDetails = Sprint(
                title=form.title.data,
                date_start=form.date_start.data,
                date_end=form.date_end.data
            )
    
            db.session.add(sprintDetails)
            db.session.commit()
            
            flash('Congratulations, sprint created!')
            return redirect(url_for('index'))
    except TypeError as e:
        print(f"Error: {e}")
        
    return render_template('sprint.html', form=form)
    
@app.route('/add-to-cycle/<int:project_id>/<int:sprint_id>/', methods=['GET','POST'])
@login_required
def add_to_cycle(project_id, sprint_id):
    if request.method == 'GET':
        # Get the sprint info for the changelog
        sprint = Sprint.query.get_or_404(sprint_id)
        project = Project.query.get_or_404(project_id)
        
        addToSprint = SprintProjectMap(
            sprint_id=sprint_id,
            project_id=project_id
        )

        db.session.add(addToSprint)
        
        # Create changelog entry
        changelog = Changelog(
            change_type='sprint_assignment',
            content=f"Project assigned to sprint: '{sprint.title}'",
            project_id=project_id,
            user_id=current_user.id
        )
        db.session.add(changelog)
        db.session.commit()
        
        flash('Congratulations, added to cycle!')
        return redirect(url_for('index'))
    return redirect(url_for('index'))
    
    
    
########################################################
### APIs for Async Updates
########################################################

@app.route('/api/project/<int:project_id>', methods=['GET'])
def api_get_project(project_id):
    project = (
        Project.query
        .filter_by(id=project_id)
        .first()
    )
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Convert SQLAlchemy model to dictionary
    project_data = {
        'id': project.id,
        'name': project.name,
        'why': project.why,
        'context': project.context,
        'launch': project.launch,
        'requirements': project.requirements,
        'dri': project.dri,
        'created': project.created.strftime('%Y-%m-%d') if project.created else None,
        'team': project.team,
        # 'status': project.status,
        # 'priority': project.priority,
        'location': project.location
    }
    
    # Return the project data as JSON
    return jsonify(project_data)

@app.route('/api/project/move', methods=['POST'])
@login_required
def api_move_project():
    """
    API endpoint to move a project to sprint, backlog, or discussion
    """
    data = request.json
    project_id = data.get('projectId')
    new_location = data.get('location')
    
    # Validate the required fields
    if not project_id or not new_location:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
    
    # Check if project exists
    project = Project.query.get(project_id)
    if project is None:
        return jsonify({"success": False, "message": "Project not found"}), 404
    
    # Record the old location for the changelog
    old_location = project.location
    
    # Update the project location
    project.location = new_location
    
    # Create changelog entry for location change
    if old_location != new_location:
        changelog = Changelog(
            change_type='location_change',
            content=f"Project moved from '{old_location}' to '{new_location}'",
            project_id=project_id,
            user_id=current_user.id,
            timestamp=datetime.utcnow()
        )
        db.session.add(changelog)
    
    # If project is moving out of sprint, remove it from sprint mappings
    if old_location == 'sprint' or new_location != 'sprint':
        # Find all sprint mappings for this project and remove them
        sprint_mappings = SprintProjectMap.query.filter_by(project_id=project_id).all()
        for mapping in sprint_mappings:
            # Add changelog for sprint removal
            sprint = Sprint.query.get(mapping.sprint_id)
            sprint_name = sprint.title if sprint else "Unknown Sprint"
            
            removal_changelog = Changelog(
                change_type='sprint_removal',
                content=f"Project removed from sprint: '{sprint_name}'",
                project_id=project_id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(removal_changelog)
            
            # Delete the mapping
            db.session.delete(mapping)
    
    # Commit changes to the database
    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Project moved to {new_location} successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Database error: {str(e)}"
        }), 500
        
        
        
@app.route('/project/<int:project_id>/add_comment', methods=['POST'])
@login_required
def add_comment(project_id):
    project = Project.query.filter_by(id=project_id).first_or_404()
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            project_id=project_id,
            user_id=current_user.id
        )
        
        db.session.add(comment)
        db.session.commit()
        
        flash('Comment added successfully!', 'success')
    else:
        flash('Error adding comment. Please check your input.', 'danger')
    
    return redirect(url_for('project', project_id=project_id))

@app.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first_or_404()
    
    # Check if current user is the author of the comment
    if comment.user_id != current_user.id:
        flash('You do not have permission to edit this comment.', 'danger')
        return redirect(url_for('project', project_id=comment.project_id))
    
    form = CommentForm()
    
    if request.method == 'GET':
        form.content.data = comment.content
    
    if form.validate_on_submit():
        comment.content = form.content.data
        db.session.commit()
        
        flash('Comment updated successfully!', 'success')
        return redirect(url_for('project', project_id=comment.project_id))
    
    return render_template('edit_comment.html', form=form, comment=comment)

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first_or_404()
    
    # Check if current user is the author of the comment
    if comment.user_id != current_user.id:
        flash('You do not have permission to delete this comment.', 'danger')
        return redirect(url_for('project', project_id=comment.project_id))
    
    project_id = comment.project_id
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Comment deleted successfully!', 'success')
    return redirect(url_for('project', project_id=project_id))
    
    
########################################################
### Manage Cycles
########################################################

@app.route('/cycles/', methods=['GET', 'POST'])
def show_cycles():
    cycles = (
        Sprint.query
        .all()
    )
    form = CreateSprint()
    
    try:
        if request.method == 'POST':
            sprintDetails = Sprint(
                title=form.title.data,
                date_start=form.date_start.data,
                date_end=form.date_end.data
            )
    
            db.session.add(sprintDetails)
            db.session.commit()
            
            flash('Congratulations, sprint created!')
            return redirect(url_for('index'))
    except TypeError as e:
        print(f"Error: {e}")
    return render_template('cycles.html', title='Naked Roadmap - View All Cycles', cycles=cycles, form=form)
    
    
@app.route('/cycles/details/<int:cycle_id>', methods=['GET', 'POST'])
def show_cycle_details():
    cycles = (
        Sprint.query
        .all()
    )
    selected_cycle = next((s for s in cycles if s.id == cycle_id), None)
    
    form = CreateSprint()
    
    try:
        if request.method == 'POST':
            sprintDetails = Sprint(
                title=form.title.data,
                date_start=form.date_start.data,
                date_end=form.date_end.data
            )
    
            db.session.add(sprintDetails)
            db.session.commit()
            
            flash('Congratulations, sprint created!')
            return redirect(url_for('index'))
    except TypeError as e:
        print(f"Error: {e}")
    return render_template('cycles.html', title='Naked Roadmap - View All Cycles', cycles=cycles, form=form, selected_cycle=selected_cycle)
    
    
########################################################
### Cycle Planning Process
########################################################
    
@app.route('/planning/')
@login_required
def plan_sprint():
    projects = (
        Project.query
        .order_by(Project.created.desc())
        .all()
    )
    goals = (
        Goal.query
        .order_by(Goal.created.desc())
        .all()
    )
    
    sprints = (
        Sprint.query
        .filter(Sprint.status != "Completed")
        .order_by(Sprint.date_start.asc())
        .all()
    )
    
    # Find recommended sprint (next upcoming sprint or current sprint)
    today = datetime.now()
    recommended_sprint = None
    
    for sprint in sprints:
        # If sprint starts in the future or is currently active
        if sprint.date_end >= today.date():
            recommended_sprint = sprint
            break
    
    sprintlog = (
        SprintProjectMap.query
        .order_by(SprintProjectMap.order.asc())
        .all()
    )
    
    return render_template(
        'plan-cycle-1.html', 
        title='Plan a Cycle', 
        projects=projects, 
        goals=goals, 
        config=Config, 
        sprints=sprints, 
        recommended_sprint=recommended_sprint,
        sprintlog=sprintlog, 
        datetime=datetime, 
        today=today
    )

@app.route('/planning/cycle/<int:sprint_id>', methods=['GET'])
def planningStep2CycleSelected(sprint_id):
    projects = (
        Project.query
        .order_by(Project.created.desc())
        .filter(Project.location == "discussion")
        .all()
    )
    goals = (
        db.session.query(
            Goal,
            func.count(SprintProjectMap.id).label('sprint_project_count')
        )
        .outerjoin(Project, Project.objective_id == Goal.id)
        .outerjoin(SprintProjectMap, (SprintProjectMap.project_id == Project.id) & 
                                     (SprintProjectMap.sprint_id == sprint_id))
        .filter(Goal.status == 'Active')
        .group_by(Goal.id)
        .order_by(Goal.created.desc())
        .all()
    )
    selectedsprint = (
        Sprint.query
        .filter(Sprint.id == sprint_id)
        .first()
    )
    # Get all sprints ordered by start date
    sprints = (
        Sprint.query
        .filter(Sprint.status != "Completed")
        .order_by(Sprint.date_start.asc())
        .all()
    )
    sprintlog = (
        SprintProjectMap.query
        .filter(SprintProjectMap.sprint_id == sprint_id)
        .order_by(SprintProjectMap.order.asc())
        .all()
    )
    today = datetime.now()
    
    return render_template(
        'plan-cycle-2.html', 
        title='Plan a Cycle', 
        projects=projects, 
        goals=goals, 
        config=Config, 
        sprints=sprints, 
        sprintlog=sprintlog, 
        datetime=datetime, 
        today=today,
        selectedsprint=selectedsprint
    )
    
@app.route('/planning/cycle/create', methods=['GET', 'POST'])
def planningStep2CycleCreation():
    form = CreateSprint()
    
    try:
        if request.method == 'POST':
            new_cycle = Sprint(
                title=form.title.data,
                date_start=form.date_start.data,
                date_end=form.date_end.data
            )
    
            db.session.add(new_cycle)
            db.session.commit()

            flash('Congratulations, sprint created!')
            return redirect(url_for(planningStep2CycleSelected), sprint_id=new_cycle.id)
    except TypeError as e:
        print(f"Error: {e}")
    
    
########################################################
### API Routes for Sprint Selection
########################################################

@app.route('/api/sprint/<int:sprint_id>', methods=['GET'])
def api_get_sprint(sprint_id):
    """API endpoint to get sprint details including associated projects"""
    sprint = Sprint.query.get_or_404(sprint_id)
    
    # Get all projects associated with this sprint
    sprint_projects = SprintProjectMap.query.filter_by(sprint_id=sprint_id).all()
    
    # Build the response data
    sprint_data = {
        'id': sprint.id,
        'title': sprint.title,
        'date_start': sprint.date_start.isoformat() if sprint.date_start else None,
        'date_end': sprint.date_end.isoformat() if sprint.date_end else None,
        'projects': []
    }
    
    # Add project data
    for entry in sprint_projects:
        project = Project.query.get(entry.project_id)
        if project:
            sprint_data['projects'].append({
                'id': project.id,
                'name': project.name,
                'status': entry.status,
                'goal': entry.goal,
                'dri': project.dri,
                'team': project.team
            })
    
    return jsonify({'success': True, 'sprint': sprint_data})

@app.route('/api/create_sprint', methods=['POST'])
@login_required
def api_create_sprint():
    """API endpoint to create a new sprint and return its details"""
    form = CreateSprint()
    
    if form.validate_on_submit():
        try:
            new_sprint = Sprint(
                title=form.title.data,
                date_start=form.date_start.data,
                date_end=form.date_end.data
            )
            
            db.session.add(new_sprint)
            db.session.commit()
            
            # Return the new sprint data
            sprint_data = {
                'id': new_sprint.id,
                'title': new_sprint.title,
                'date_start': new_sprint.date_start.isoformat() if new_sprint.date_start else None,
                'date_end': new_sprint.date_end.isoformat() if new_sprint.date_end else None
            }
            
            return jsonify({'success': True, 'sprint': sprint_data})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    
    return jsonify({'success': False, 'message': 'Form validation failed'})

@app.route('/api/project/commit_to_sprint', methods=['POST'])
@login_required
def api_commit_to_sprint():
    """API endpoint to commit a project to the selected sprint or update its goal"""
    data = request.json
    project_id = data.get('projectId')
    sprint_id = data.get('sprintId')
    goal = data.get('goal', '')
    sprint_project_id = data.get('sprintProjectId')
    
    if not project_id or not sprint_id:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    # Check if project and sprint exist
    project = Project.query.get_or_404(project_id)
    sprint = Sprint.query.get_or_404(sprint_id)
    
    # If sprint_project_id is provided, update existing record
    if sprint_project_id:
        existing = SprintProjectMap.query.get(sprint_project_id)
        if existing:
            old_goal = existing.goal
            existing.goal = goal
            
            # Add changelog entry if goal changed
            if old_goal != goal:
                changelog = Changelog(
                    change_type='sprint_goal_update',
                    content=f"Sprint goal updated from '{old_goal}' to '{goal}'",
                    project_id=project_id,
                    user_id=current_user.id,
                    timestamp=datetime.utcnow()
                )
                db.session.add(changelog)
            
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Project goal updated in sprint',
                'sprintProjectId': existing.id
            })
        else:
            return jsonify({'success': False, 'message': 'Sprint project mapping not found'})
    
    # Check if this project is already in this sprint
    existing = SprintProjectMap.query.filter_by(
        project_id=project_id,
        sprint_id=sprint_id
    ).first()
    
    if existing:
        # Update the goal if it's changed
        old_goal = existing.goal
        if existing.goal != goal:
            existing.goal = goal
            
            # Add changelog entry
            changelog = Changelog(
                change_type='sprint_goal_update',
                content=f"Sprint goal updated from '{old_goal}' to '{goal}'",
                project_id=project_id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(changelog)
        
        # Ensure project location is set to 'active' when in sprint
        if project.location != 'active':
            old_location = project.location
            project.location = 'active'
            
            # Add changelog for location change
            location_changelog = Changelog(
                change_type='location_change',
                content=f"Project moved from '{old_location}' to 'active'",
                project_id=project_id,
                user_id=current_user.id,
                timestamp=datetime.utcnow()
            )
            db.session.add(location_changelog)
            
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Project goal updated in sprint',
            'sprintProjectId': existing.id
        })
    
    # Create new sprint-project mapping
    # First, get count of current projects to set the order
    current_count = SprintProjectMap.query.filter_by(sprint_id=sprint_id).count()
    
    new_mapping = SprintProjectMap(
        sprint_id=sprint_id,
        project_id=project_id,
        goal=goal,
        status="Planned",
        order=current_count + 1,
        added=datetime.utcnow()
    )
    
    db.session.add(new_mapping)
    
    # Update project location to 'active' when added to sprint
    old_location = project.location
    project.location = 'active'
    
    # Add changelog for location change
    changelog_location = Changelog(
        change_type='location_change',
        content=f"Project moved from '{old_location}' to 'active'",
        project_id=project_id,
        user_id=current_user.id,
        timestamp=datetime.utcnow()
    )
    db.session.add(changelog_location)
    
    # Add changelog entries for sprint assignment
    changelog_sprint = Changelog(
        change_type='sprint_assignment',
        content=f"Project assigned to sprint: '{sprint.title}' with goal: '{goal}'",
        project_id=project_id,
        user_id=current_user.id,
        timestamp=datetime.utcnow()
    )
    
    db.session.add(changelog_sprint)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Project committed to sprint successfully',
            'sprintProjectId': new_mapping.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
        
        
@app.route('/api/projects/reorder', methods=['POST'])
@login_required
def reorder_projects():
    """API endpoint to update the order of projects in a sprint"""
    data = request.json
    
    if not data or 'projects' not in data:
        return jsonify({'success': False, 'message': 'Missing project order data'})
    
    try:
        # Begin transaction
        for project_data in data['projects']:
            sprint_project = SprintProjectMap.query.get(project_data['id'])
            if sprint_project:
                sprint_project.order = project_data['order']
                
                # Add changelog entry for significant order changes (optional)
                # Only log if order changed by more than 2 positions to avoid clutter
                old_order = getattr(sprint_project, 'order', 0) or 0
                new_order = project_data['order']
                if abs(old_order - new_order) > 2:
                    changelog = Changelog(
                        change_type='project_reorder',
                        content=f"Project priority changed from position {old_order} to {new_order}",
                        project_id=sprint_project.project_id,
                        user_id=current_user.id
                    )
                    db.session.add(changelog)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Project order updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/project/toggle_critical', methods=['POST'])
@login_required
def toggle_project_critical():
    """API endpoint to toggle a project's critical status"""
    data = request.json
    
    if not data or 'sprintProjectId' not in data or 'critical' not in data:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    sprint_project_id = data['sprintProjectId']
    critical_status = data['critical']
    
    try:
        sprint_project = SprintProjectMap.query.get_or_404(sprint_project_id)
        
        # Update the critical status
        old_status = sprint_project.critical
        sprint_project.critical = critical_status
        
        # Add changelog entry if status changed
        if old_status != critical_status:
            status_text = "critical" if critical_status else "non-critical"
            changelog = Changelog(
                change_type='critical_status_change',
                content=f"Project marked as {status_text}",
                project_id=sprint_project.project_id,
                user_id=current_user.id
            )
            db.session.add(changelog)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Project critical status updated to {critical_status}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})