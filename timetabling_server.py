# Timetabling System Server
# Neeraj Chatlani and D.S. Myers, 2016

from flask import Flask
from flask import jsonify, request
from flask_sqlalchemy import SQLAlchemy
import json
import os
import solver
from datetime import datetime
import copy

app = Flask(__name__)

# Set up database connection
# In the sqlite location string, three slashes (///) indicates a relative path
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/schedule.db'
db = SQLAlchemy(app)

# Each database table is described by a class that extends db.Model


# Table for Timeslots
#
# Fields:
#   string_representation -- e.g. "MWF 8:00 - 8:50"
#   matrix_category -- e.g. "MWF for 50 minutes"; off-matrix slots are labeled "off-matrix"
#   monday_start
#   monday_end
#   tuesday_start
#   tuesday_end
#   Similar for other days
#
#   Start and end times are in 24-hour format
class Timeslot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    string_representation = db.Column(db.String(80))
    matrix_category = db.Column(db.String(80))
    monday_start = db.Column(db.String(8))
    monday_end = db.Column(db.String(8))
    tuesday_start = db.Column(db.String(8))
    tuesday_end = db.Column(db.String(8))
    wednesday_start = db.Column(db.String(8))
    wednesday_end = db.Column(db.String(8))
    thursday_start = db.Column(db.String(8))
    thursday_end = db.Column(db.String(8))
    friday_start = db.Column(db.String(8))
    friday_end = db.Column(db.String(8))

    def __init__(self, string_representation='', matrix_category='',
                 monday_start='', monday_end='', tuesday_start='', tuesday_end='',
                 wednesday_start='', wednesday_end='', thursday_start='',
                 thursday_end='', friday_start='', friday_end=''):
        self.string_representation = string_representation
        self.matrix_category = matrix_category
        self.monday_start = monday_start
        self.tuesday_start = tuesday_start
        self.wednesday_start = wednesday_start
        self.thursday_start = thursday_start
        self.friday_start = friday_start
        self.monday_end = monday_end
        self.tuesday_end = tuesday_end
        self.wednesday_end = wednesday_end
        self.thursday_end = thursday_end
        self.friday_end = friday_end
        
    def __repr__(self):
        return self.string_representation
    

# Table for Rooms
#
# Fields:
#   building: string
#   room_number: string
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    building = db.Column(db.String(40))
    room_number = db.Column(db.String(10))
    
    def __init__(self, building = '', room_number = ''):
        self.building = building
        self.room_number = room_number
        
    def __repr__(self):
        return '<Room %r>' % (self.building + self.room_number)



# Table for Instructors
#
# Table holds list of all instructors
class Instructor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)
    
    def __init__(self, name = ''):
        self.name = name

    def __repr__(self):
        return '<Instructor %r>' % self.name


# Table of acceptable rooms
#
# Fields:
#   section_name
#   room: e.g. "BUSH 301"
#   building
#   room_number
class AcceptableRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_name = db.Column(db.String(80))
    room = db.Column(db.String(80))
    building = db.Column(db.String(40))
    room_number = db.Column(db.String(10))
        
    def __init__(self, section_name = '', room = '', building = '', room_number = ''):
        self.section_name = section_name
        self.room = room
        self.building = building
        self.room_number = room_number
        
    def __repr__(self):
        return '<AcceptableRoom %r>' % (self.section_name + " " + self.room)
        
        
# Table for acceptable timeslots
#
# Fields:
#   section_name
#   timeslot_string: e.g. "MWF 8:00 - 8:50"
class AcceptableTimeslot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_name = db.Column(db.String(80))
    timeslot_string = db.Column(db.String(80))
    
    def __init__(self, section_name = '', timeslot_string = ''):
        self.section_name = section_name
        self.timeslot_string = timeslot_string
        
    def __repr__(self):
        return '<AcceptableRoom %r>' % (self.section_name + " " + self.timeslot_string)
        
        
# Table for basic section information
#
# Fields:
#   section_name -- the name of the section, e.g. 'CMS 167 - Lecture 1'
#   course_prefix -- the three letter course code, e.g. 'CMS'
#   course_number -- stored as a String, e.g. '170 H1X'
#   is_lab -- True if the section is a lab, False otherwise
#   instructor -- name of the instructor
#   course_title -- e.g. 'Problem Solving I with Java'
#   acceptable_room -- list of acceptable rooms
class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_name = db.Column(db.String(80), unique=True)
    course_prefix = db.Column(db.String(8))
    course_number = db.Column(db.String(24))
    course_title = db.Column(db.String(120))
    is_lab = db.Column(db.Boolean)
    instructor = db.Column(db.String(80))
    is_holt = db.Column(db.Boolean)
    is_crosslisted = db.Column(db.Boolean)
    assigned_timeslot = db.Column(db.String(80))
    assigned_room = db.Column(db.String(80))
    

    def __init__(self, section_name, course_prefix = '', course_number = '', 
                 is_lab = False,  course_title = '', is_holt = False, is_cross = False, instructor = ''):
        self.section_name = section_name
        self.course_prefix = course_prefix
        self.course_number = course_number
        self.is_lab = is_lab
        self.instructor = instructor
        self.course_title = course_title
        self.is_holt = is_holt
        self.is_crosslisted = is_cross
        self.assigned_timeslot = None
        self.assigned_room = None

    def __repr__(self):
        return '<Section %r>' % (self.section_name + ' ' + str(self.is_holt) + ' ' + str(self.is_crosslisted))
        
        
# A conflict between two courses
#
# Fields:
#   first_course
#   second_course
#   severity: Heavy, Medium, or Light
class Conflict(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_course = db.Column(db.String(80))
    second_course = db.Column(db.String(80))
    severity = db.Column(db.String(20))
    
    def __init__(self, first_course, second_course, severity):
        self.first_course = first_course
        self.second_course = second_course
        self.severity = severity
        
    def __repr__(self):
        return '<Conflict %r>' % (self.first_course + ' ' 
                                  + self.second_course + ' ' + self.severity)
                                  

# Main entry point: returns initial front-end page
@app.route('/')
def index():
    return app.send_static_file('timetabling_system.html')
    

# Creates new object entries for new section sections entered by a user
#
# Inputs from client:
#   A JSON string containing a list of new section names
#
# Effects:
#   Creates a new object to store information on each new section
#
# Returns:
#   Nothing
@app.route('/create_new_sections', methods=['POST'])
def create_new_sections():
    
    # Unpack the name list from the request's JSON content
    content = request.get_json()
    print content
    
    new_section_names = content['names']
    course_prefix = content['prefix']
    course_number = content['number']
    course_title = content['title']
    is_holt = content['is_holt']
    is_cross = content['is_cross']
    
    # Pull the existing list of sections from the database
    sections = Section.query.all()
    existing_section_names = [c.section_name for c in sections]
    
    # Create a new entry in the database for each new section name
    for name in new_section_names:
        name = name.encode('utf-8')
        
        # If name is not already in database, make a new row
        if name not in existing_section_names:
            if 'Lab' in name:
                is_lab = True
                course_title_for_this_section = "Lab for " + course_title
            else:
                is_lab = False
                course_title_for_this_section = course_title
                
            s = Section(name, course_prefix, course_number, is_lab, 
                        course_title_for_this_section, is_holt, is_cross)
                        
            db.session.add(s)
        
    # Commit the changes
    db.session.commit()

    # The calling AJAX function expects valid JSON as message contents
    # Return null, which is parsed as valid JSON by the client
    return 'null'

# Saves the udpated information for a section into the database
#
# Inputs from client:
#   A JSON string representing an object holding the values from the section
#   information input dialog. The fields are:
#     - section_name
#     - instructor
#     - course_title
#     - OTHERS TO COME...
#
# Effects:
#   Updates the database entry for the section
#
# Returns:
#   Nothing
@app.route('/save_section_information', methods=['POST'])
def save_section_information():
    
    # Get the request's JSON content
    content = request.get_json()
    
    # Update database entries
    section_info = Section.query.filter_by(section_name = content['section_name']).first()
    section_info.instructor = content['instructor'] 
    section_info.course_title = content['course_title']
    
    # Add any new acceptable rooms
    existing_rooms = AcceptableRoom.query.filter_by(section_name = content['section_name']).all()
    existing_room_names = [r.room for r in existing_rooms]
    new_room_names = filter(lambda r: r not in existing_room_names, content['acceptable_rooms'])
    
    for new_room in new_room_names:
        fields = new_room.split(' ')
        building = fields[0]
        room_number = fields[1]
        new_ar = AcceptableRoom(content['section_name'], new_room, building, room_number)
        db.session.add(new_ar);
        
    # Remove any room names that are not in content['acceptable_rooms']
    remove_room_names = filter(lambda r: r not in content['acceptable_rooms'], existing_room_names)
    for old_room in remove_room_names:
        AcceptableRoom.query.filter_by(room = old_room).filter_by(section_name = content['section_name']).delete()
        
    # Add any new acceptable timeslots
    existing_timeslots = AcceptableTimeslot.query.filter_by(section_name = content['section_name']).all()
    existing_timeslot_names = [t.timeslot_string for t in existing_timeslots]
    new_timeslot_names = filter(lambda t: t not in existing_timeslot_names, content['acceptable_timeslots'])
    
    for new_timeslot in new_timeslot_names:
        new_at = AcceptableTimeslot(content['section_name'], new_timeslot)
        db.session.add(new_at)
        
    # Remove any timeslots that are not in content['acceptable_timeslots']
    remove_timeslot_names = filter(lambda t: t not in content['acceptable_timeslots'], existing_timeslot_names)
    for old_timeslot in remove_timeslot_names:
        AcceptableTimeslot.query.filter_by(timeslot_string = old_timeslot).filter_by(section_name = content['section_name']).delete()
    
    # Add any new existing pairs of conflicts
    
    # Figure out the course name from the complete section name
    course_name = convert_section_name_to_course_name(content['section_name'])
    
    existing_conflicts = Conflict.query.filter((Conflict.first_course == course_name) |
                                                  (Conflict.second_course == course_name))
                                                  
    # Find any existing conflicts that need to have an updated severity
    conflicts = content['conflicting_courses']
    severities = content['severities']
    for ec in existing_conflicts:
        for i in range(len(conflicts)):
            if ec.first_course == course_name and ec.second_course == conflicts[i]:
                print course_name, conflicts[i], severities[i]
                ec.severity = severities[i]
            if ec.first_course == conflicts[i] and ec.second_course == course_name:
                print course_name, conflicts[i], severities[i]
                ec.severity = severities[i]
                                                  
    # Build a list of all existing conflicts
    existing_conflict_names = []
    for c in existing_conflicts:
        if c.first_course == course_name:
            existing_conflict_names.append(c.second_course)
        
        if c.second_course == course_name:
            existing_conflict_names.append(c.first_course)
    
    # Isolate the conflicts passed from the server that are not already in the database   
    new_conflicts_and_severities = []
    for i in range(len(conflicts)):
        if conflicts[i] not in existing_conflict_names:
            new_conflicts_and_severities.append((conflicts[i], severities[i]))
    
    # Enter the new conflicts in the database
    for cs in new_conflicts_and_severities:
        new_conflict = Conflict(course_name, cs[0], cs[1])
        db.session.add(new_conflict)
        

    # Identify the items in the existing conflict list that are not in the
    # current conflict list received from the client
    remove_list = filter(lambda x: x not in conflicts, existing_conflict_names)
    print remove_list
    for r in remove_list:
        Conflict.query.filter_by(first_course = course_name).filter_by(second_course = r).delete()
        Conflict.query.filter_by(first_course = r).filter_by(second_course = course_name).delete()

    db.session.commit()
    
    print Conflict.query.all()
    
    return 'null'
    

# Return the section information for the given section name
#
# Inputs from client:
#   A JSON string containing the name of the section
#
# Effects:
#   None (reads from data store)
#
# Returns:
#   A JSON string containing any information in the data store
#   for the given section name
@app.route('/get_section_information', methods=['POST'])
def get_section_information():

    # Unpack the name list from the request's JSON content
    content = request.get_json()
    name = content['name']
    
    # Basic section information
    section_info = Section.query.filter_by(section_name = name).first()
    
    # Acceptable rooms
    acceptable_rooms = AcceptableRoom.query.filter_by(section_name = name).all()
    acceptable_room_names = [r.room for r in acceptable_rooms]
    
    #Acceptable timeslots
    accepted_timeslots = AcceptableTimeslot.query.filter_by(section_name = name).all()
    acceptable_timeslots = [r.timeslot_string for r in accepted_timeslots]
    
    # Construct and send the response
    response = {}
    response['section_name'] = section_info.section_name
    response['course_title'] = section_info.course_title
    response['is_lab'] = section_info.is_lab
    response['instructor'] = section_info.instructor
    response['acceptable_rooms'] = acceptable_room_names
    response['acceptable_timeslots'] = acceptable_timeslots
        
    print response

    return jsonify(**response)
    
# Returns a list of the assigned conflicts for a given class    
@app.route('/get_conflicts', methods=['POST'])
def get_conflicts():
    content = request.get_json()
    name = content['name']
    
    # Construct the course name
    fields = name.split(' ')
    course_name = fields[0] + ' ' + fields[1]
    if ('H' in fields[4] and 'X' in fields[4]):
        course_name += ' - HX'
    elif ('H' in fields[4]):
        course_name += ' - H'
    elif ('X' in fields[4]):
        course_name += ' - X'
        
    print course_name
        
    # Query the database for anything matching the name
    existing_conflicts = Conflict.query.filter((Conflict.first_course == course_name) |
                                                  (Conflict.second_course == course_name)).all()
    
    print existing_conflicts
                                                  
    names = []
    severities = []
    for c in existing_conflicts:
        if course_name == c.first_course:
            names.append(c.second_course)
        elif course_name == c.second_course:
            names.append(c.first_course)
        
        severities.append(c.severity)
        
    response = {}
    response['conflicts'] = names
    response['severities'] = severities
    
    return jsonify(response)
    
# Returns the course prefix, number, and number of sections and labs for a 
# given course
@app.route('/get_course_information', methods=['POST'])
def get_course_information():
    
    # Unpack the name list from the request's JSON content
    content = request.get_json()
    name = content['name']
    
    fields = name.split(' ')
    prefix = fields[0]
    number = fields[1]
    
    section_results = Section.query.filter_by(course_prefix = prefix).filter_by(course_number = number).all()
    
    title = section_results[0].course_title
    
    num_lectures = len(filter(lambda x: 'Lecture' in x.section_name, section_results))
    num_labs = len(filter(lambda x: 'Lab' in x.section_name, section_results))

    response = {"course_title" : title, "num_lectures" : num_lectures, "num_labs" : num_labs}
    return jsonify(response)



# Returns the list of instructors
#
# Inputs from client:
#   None
#
# Effects:
#   None
#
# Returns:
#   A JSON string containing the list of instructors from the
#   Instructor database table
@app.route('/get_instructor_names', methods=['GET'])
def get_instructor_names():
    
    # Query the database for instructor names
    instructors = Instructor.query.all()
    name_list = [inst.name for inst in instructors]
    
    response = {"names" : name_list}
    return jsonify(**response)
    


# Returns the list of existing section names in the database
#
# Inputs from client:
#   None
#
# Effects:
#   None
#
# Returns:
#   A JSON string containing the list of section names from the
#   Section database table
@app.route('/get_section_names', methods=['GET'])
def get_section_names():
    
    # Query the database for section names
    sections = Section.query.all()
    sec_list = [inst.section_name for inst in sections]
    
    # Wrap and send dict of names
    response = {"names" : sec_list}
    return jsonify(**response)
    


# Returns the list of existing building names in the database
#
# Inputs from client:
#   None
#
# Effects:
#   None
#
# Returns:
#   A JSON string containing the list of buildings names from the
#   Room database table
@app.route('/get_buildings', methods=['GET'])
def get_building_names():
    
    # Query the database for buildings
    rooms = Room.query.all()
    b_list = [inst.building for inst in rooms]
    
    # Remove duplicates
    b_list = list(set(b_list))

    # Wrap and send dict of buildling names
    response = {"buildings" : b_list}
    return jsonify(**response)


# Returns the full list of prefixes on load and when a new prefix is added    
@app.route('/get_prefixes', methods=['GET'])
def get_prefixes():
    
    # Query the database for buildings
    sections = Section.query.all()
    p_list = [inst.course_prefix for inst in sections]
    
    # Remove duplicates
    p_list = list(set(p_list))

    # Wrap and send dict of buildling names
    response = {"prefixes" : p_list}
    return jsonify(**response)    
    


# Returns the list of room numbers for a given building name
#
# Inputs from client:
#   A JSON string containing the name of the building
#
# Effects:
#   None
#
# Returns:
#   A JSON string containing the list of room numbers in the given building 
#   from the Room database table
@app.route('/get_rooms_by_building', methods=['POST'])
def get_rooms_by_building():
    
    # Unpack the name list from the request's JSON content
    content = request.get_json()
    
    building_name = content['building']
    
    # Query the database for the given section
    matching_rooms = Room.query.filter_by(building = building_name)
    room_number_list = [building_name + ' ' + r.room_number for r in matching_rooms]

    # JSON response
    response = {"rooms" : room_number_list}
    return jsonify(**response)


# Returns a list of all the course sections with a given prefix    
@app.route('/get_sections_by_prefix', methods=['POST'])
def get_sections_by_prefix():
     
    content = request.get_json()
    prefix = content['prefix']
     
    matching_sections = Section.query.filter_by(course_prefix = prefix)
    section_list = [r.section_name for r in matching_sections]
    
    response = {"sections" : section_list}
    return jsonify(**response)
    
    
# Returns a list of all the courses with a given prefix   
@app.route('/get_courses_by_prefix', methods=['POST'])
def get_courses_by_prefix():
     
    content = request.get_json()
    prefix = content['prefix']
     
    matching_courses = Section.query.filter_by(course_prefix = prefix)
    section_list = [r.section_name for r in matching_courses]
    #course_list = [r.course_prefix + " " + r.course_number for r in matching_courses]
    
    response = {"courses" : section_list}
    return jsonify(**response)    


# Returns a list of the timeslots given a category of days and amount of time    
@app.route('/get_timeslots_by_category', methods=['POST'])
def get_timeslots_by_category():
    
    # Unpack the category name from the request's JSON content
    content = request.get_json()
    timeslot_category = content['category']
    
    # Query the database for the given category
    matching_timeslots = Timeslot.query.filter_by(matrix_category = timeslot_category)
    timeslot_list = [r.string_representation for r in matching_timeslots]
    
    # JSON response
    response = {"timeslots" : timeslot_list}
    return jsonify(**response)
    

#Deletes the selected section and its information from the database    
@app.route('/delete_section', methods=['POST'])
def delete_section():
    
    #Unpack the category name from the request's JSON content
    content = request.get_json()
    name = content['name']
    
    # Remove all entries related to the section from the database
    Section.query.filter_by(section_name = name).delete()
    AcceptableRoom.query.filter_by(section_name = name).delete()
    AcceptableTimeslot.query.filter_by(section_name = name).delete()
    Conflict.query.filter_by(first_course = name).delete()
    Conflict.query.filter_by(second_course = name).delete()
    
    db.session.commit()
    
    return 'null'
    
    
def convert_section_name_to_course_name(name):
    fields = name.split(' ')
    course_name = fields[0] + ' ' + fields[1]
    if ('H' in fields[4] and 'X' in fields[4]):
        course_name += ' - HX'
    elif ('H' in fields[4]):
        course_name += ' - H'
    elif ('X' in fields[4]):
        course_name += ' - X'
        
    return course_name
    

# Returns True if two timeslot strings overlap
#
# Inputs:
#   The two timeslots in day and 24-hour format, e.g. "MWF 14:00 - 14:50"
#   Custom timeslots have their components separated by " ; "
#
# Returns:
#   True if the timeslots overlap
def are_overlapping_timeslots(slot1, slot2):
    
    # The slots may be custom composites
    # Split into the component parts
    slot1_components = slot1.split(' ; ')
    slot2_components = slot2.split(' ; ')
    
    # Compare all components of the two timeslots to see if they overlap
    # in any part
    for t1 in slot1_components:
        for t2 in slot2_components:
            
            # Extract the meeting days 
            fields1 = t1.split(' ')
            fields2 = t2.split(' ')
            
            days1 = fields1[0]
            days2 = fields2[0]
            
            for d in 'MTWRF':
                
                # Only check pairs that meet on the same day
                if d not in days1 or d not in days2:
                    continue
                
                # The times overlap if the start time for one occurs between
                # the start and end times of the other
                start_time_1 = fields1[1]
                end_time_1 = fields1[3]
                start_time_2 = fields2[1]
                end_time_2 = fields2[3]
                
                print start_time_1, end_time_1, start_time_2, end_time_2
                
                if ((start_time_1 >= start_time_2 and start_time_1 <= end_time_2) or
                    (start_time_2 >= start_time_1 and start_time_2 <= end_time_1)):
                        
                        print str(start_time_1 >= start_time_2 and start_time_1 <= end_time_2)
                        print str(start_time_2 >= start_time_1 and start_time_2 <= end_time_1)

                        # Stop checking once we find a single overlap
                        return True
                        
    # All checks are complete and no overlaps were found
    return False
    

# Identify the heavy, medium, and light conflicts for a given course at
# a given timeslot
def identify_conflicts(name, timeslot):
    
    course_name = convert_section_name_to_course_name(name)

    potential_conflicts = Conflict.query.filter((Conflict.first_course == course_name) |
                                                (Conflict.second_course == course_name))
                                  
    heavy_conflicts = []
    medium_conflicts = []
    light_conflicts = []
    for c in potential_conflicts:
        
        # Look up the sections of the other course
        if c.first_course == course_name:
            lookup_course = c.second_course
        else:
            lookup_course = c.first_course
            
        fields = lookup_course.split(' ')
        prefix = fields[0]
        number= fields[1]
        is_holt = False
        is_crosslisted = False
        if len(fields) == 4:
            if 'H' in fields[3]:
                is_holt = True
            if 'X' in fields[3]:
                is_crosslisted = True
            
        query = Section.query.filter_by(course_prefix = prefix)
        query = query.filter_by(course_number = number)
        query = query.filter_by(is_holt = is_holt)
        query = query.filter_by(is_crosslisted = is_crosslisted)
        lookup_course_sections = query.all()

        # Check if any sections of the other course have an overlapping timeslot
        for t in lookup_course_sections:
            
            if are_overlapping_timeslots(t.assigned_timeslot, timeslot):
                conflict_exists = True
            else:
                conflict_exists = False
        
            # If so, store it as a heavy, medium, or light conflict
            if conflict_exists:
                if c.severity == 'Heavy':
                    heavy_conflicts.append(t.section_name)
                elif c.severity == 'Medium':
                    medium_conflicts.append(t.section_name)
                elif c.severity == 'Light':
                    light_conflicts.append(t.section_name)
    
    return heavy_conflicts, medium_conflicts, light_conflicts
    
#Returns the conflicts of a given course according to their severity
@app.route('/get_assigned_timeslot_room_and_conflicts', methods=['POST'])
def get_assigned_timeslot_room_and_conflicts():
    
    # Unpack the category name from the request's JSON content
    content = request.get_json()
    name = content['name']

    s = Section.query.filter_by(section_name = name).first()
    
    # Figure out which potential conflicts are actually in conflict
    course_name = convert_section_name_to_course_name(name)

    potential_conflicts = Conflict.query.filter((Conflict.first_course == course_name) |
                                                (Conflict.second_course == course_name))
                                  
    heavy_conflicts = []
    medium_conflicts = []
    light_conflicts = []
    for c in potential_conflicts:
        
        # Look up the sections of the other course
        if c.first_course == course_name:
            lookup_course = c.second_course
        else:
            lookup_course = c.first_course
            
        fields = lookup_course.split(' ')
        prefix = fields[0]
        number= fields[1]
        is_holt = False
        is_crosslisted = False
        if len(fields) == 4:
            if 'H' in fields[3]:
                is_holt = True
            if 'X' in fields[3]:
                is_crosslisted = True
            
        query = Section.query.filter_by(course_prefix = prefix)
        query = query.filter_by(course_number = number)
        query = query.filter_by(is_holt = is_holt)
        query = query.filter_by(is_crosslisted = is_crosslisted)
        lookup_course_sections = query.all()

        # Check if any sections of the other course have an overlapping timeslot
        for t in lookup_course_sections:
            
            print t.assigned_timeslot, s.assigned_timeslot
            
            if are_overlapping_timeslots(t.assigned_timeslot, s.assigned_timeslot):
                conflict_exists = True
            else:
                conflict_exists = False
        
            # If so, store it as a heavy, medium, or light conflict
            if conflict_exists:
                if c.severity == 'Heavy':
                    heavy_conflicts.append(t.section_name)
                elif c.severity == 'Medium':
                    medium_conflicts.append(t.section_name)
                elif c.severity == 'Light':
                    light_conflicts.append(t.section_name)
    
    print heavy_conflicts, medium_conflicts, light_conflicts

    # Return JSON response
    response = {'assigned_timeslot' : s.assigned_timeslot, 
                'assigned_room' : s.assigned_room,
                'heavy_conflicts' : heavy_conflicts,
                'medium_conflicts' : medium_conflicts,
                'light_conflicts' : light_conflicts}
    return jsonify(**response)
    
    
# Returns the rooms that are available and the conflicts that would be incurred
# if a given course is assigned a given timeslot
@app.route('/get_conflicts_and_rooms_at_timeslot', methods=['POST'])
def get_conflicts_and_rooms_at_timeslot():
    
    # Unpack the category name from the request's JSON content
    content = request.get_json()
    name = content['name']
    proposed_timeslot = content['timeslot']
    room_list = []
    conflict_list = []
    
    # Pull the acceptable rooms for this course from the database
    acceptable_rooms = AcceptableRoom.query.filter_by(section_name = name).all()
    print acceptable_rooms
    
    # Check if any class is assigned to the same room at an overlapping timeslot
    for r in acceptable_rooms:
        courses_assigned_to_room = Section.query.filter_by(assigned_room = r.room).all()
        courses_assigned_to_room = filter(lambda x: x.section_name != name, courses_assigned_to_room)
        print courses_assigned_to_room
        
        conflict_exists = False
        
        for c in courses_assigned_to_room:
            room_timeslot = c.assigned_timeslot
            
            if are_overlapping_timeslots(room_timeslot, proposed_timeslot):
                conflict_exists = True
                
        # If there is no conflict, add the room to the room list
        if not conflict_exists:
            room_list.append(r.room)
    
    
    heavy_conflicts, medium_conflicts, light_conflicts = identify_conflicts(name, proposed_timeslot)
    
    
    # Return the response
    response = {'rooms' : room_list, 'heavy_conflicts' : heavy_conflicts,
                'medium_conflicts': medium_conflicts, 'light_conflicts':light_conflicts}
    return jsonify(**response)


# Assigns a new timeslot and room to a section    
@app.route('/set_assigned_timeslot_and_room', methods=['POST'])
def set_assigned_timeslot_and_room():
    
    # Unpack the category name from the request's JSON content
    content = request.get_json()
    name = content['name']
    new_timeslot = content['timeslot']
    new_room = content['room']
    
    print name, new_timeslot, new_room
    
    s = Section.query.filter_by(section_name = name).first()
    s.assigned_timeslot = new_timeslot
    s.assigned_room = new_room
    
    db.session.commit()
    
    return "null"


#Runs the scheduler on the current list of courses    
@app.route('/schedule_with_one_pass', methods=['GET'])
def schedule_with_one_pass():
    
    # Pull rooms from the database
    room_results = Room.query.all();
    room_list = [r.building + '_' + r.room_number for r in room_results]
    print room_list
    
    # Pull list of timeslots from the database
    # Getting the list of all acceptable timeslots and reduce it to its unique components
    acceptable_timeslot_results = AcceptableTimeslot.query.all();
    timeslots_with_duplicates = [a.timeslot_string for a in acceptable_timeslot_results]
    unique_timeslot_strings = list(set(timeslots_with_duplicates))
    print unique_timeslot_strings
    
    # Convert the timeslots string to 12-hour format
    #
    # This is required for backwards-compatibility with the previous solver
    # and old input file formats
    timeslots_12_hour = []
    timeslots_24_hour = []
    for t in unique_timeslot_strings:
        new_string = ''
        
        fields = t.split(' ')
        new_string += fields[0] + ' '
        d = datetime.strptime(fields[1], "%H:%M")
        new_string += d.strftime("%I:%M %p")
        new_string += ' - '
        d = datetime.strptime(fields[3], "%H:%M")
        new_string += d.strftime("%I:%M %p")
        
        new_string = new_string.replace('AM', 'am')
        new_string = new_string.replace('PM', 'pm')

        timeslots_12_hour.append(new_string)
        timeslots_24_hour.append(t)
    
    timeslot_ids = range(len(unique_timeslot_strings))

    # Assign each timeslot a unique id
    timeslots_with_ids = [str(i) + ' ' + timeslots_12_hour[i] for i in range(len(timeslots_12_hour))]
    print timeslots_with_ids
    
    # Pull the list of instructors from the database
    instructor_results = Instructor.query.all();
    instructors = [i.name for i in instructor_results]
    print instructors
    
    # Build the vertices structure with one entry per section
    section_results = Section.query.all();
    
    # Keep track of the name transformations so we can undo them after the
    # schedule has been constructed
    transformed_to_original_names_map = {}
    
    vertices = {}
    for s in section_results:
        new_section = {}
        
        fields = s.section_name.split(' ')
        prefix = fields[0]
        number = fields[1]
        dash = fields[2]
        lecture_or_lab = fields[3]
        section_number = fields[4]
        
        section_name = prefix + '_' + number + '_' + section_number
        if lecture_or_lab.lower() == 'lab':
            section_name += '_LAB'
    
        new_section['name'] = section_name
        transformed_to_original_names_map[section_name] = s.section_name
    
        # Get the acceptable rooms
        acceptable_rooms = AcceptableRoom.query.filter_by(section_name = s.section_name).all()
        new_section['acceptable_rooms'] = [r.building + '_' + r.room_number for r in acceptable_rooms]
        
        # Get the acceptable timeslot ids
        acceptable_timeslots = AcceptableTimeslot.query.filter_by(section_name = s.section_name).all()
        acceptable_timeslot_ids = [unique_timeslot_strings.index(a.timeslot_string) for a in acceptable_timeslots]
        new_section['acceptable_timeslots'] = acceptable_timeslot_ids
        
        # Instructor
        instructor = s.instructor
        instructor = instructor.replace(',', '')
        instructor = instructor.replace('.', '')
        instructor = instructor.replace(' ', '_')
        new_section['instructor'] = instructor
        
        print new_section
        
        vertices[section_name] = new_section
        
    # Intialize unavailable rooms for each acceptable timeslot
    for course in vertices:
        for timeslot in vertices[course]['acceptable_timeslots']:
            vertices[course][timeslot] = {}
            vertices[course][timeslot]['unassigned_rooms'] = copy.copy(vertices[course]['acceptable_rooms'])
            
            vertices[course][timeslot]['conflict_penalty'] = 0.0
            vertices[course][timeslot]['proximity_penalty'] = 0.0
    
    # Initialize the set of conflicts
    conflict_query_results = Conflict.query.all()
    conflicts = []
    
    for c in conflict_query_results:
        print c
        first_course = c.first_course
        second_course = c.second_course
        severity = c.severity
        
        # Get the sections of the first course
        fields = first_course.split(' ')
        prefix = fields[0]
        number= fields[1]
        is_holt = False
        is_crosslisted = False
        if len(fields) == 4:
            if 'H' in fields[3]:
                is_holt = True
            if 'X' in fields[3]:
                is_crosslisted = True
            
        query = Section.query.filter_by(course_prefix = prefix)
        query = query.filter_by(course_number = number)
        query = query.filter_by(is_holt = is_holt)
        query = query.filter_by(is_crosslisted = is_crosslisted)
        first_course_sections = query.all()
        print first_course, first_course_sections
        
        # Get the sections of the second course
        fields = second_course.split(' ')
        prefix = fields[0]
        number= fields[1]
        is_holt = False
        is_crosslisted = False
        if len(fields) == 4:
            if 'H' in fields[3]:
                is_holt = True
            if 'X' in fields[3]:
                is_crosslisted = True
            
        query = Section.query.filter_by(course_prefix = prefix)
        query = query.filter_by(course_number = number)
        query = query.filter_by(is_holt = is_holt)
        query = query.filter_by(is_crosslisted = is_crosslisted)
        second_course_sections = query.all()
        print second_course, second_course_sections
        
        # Weight the severity by the number of sections
        num_first_course_sections = len(first_course_sections)
        num_second_course_sections = len(second_course_sections)
        
        if severity == 'Heavy':
            weight = 12
        elif severity == 'Medium':
            weight = 6
        elif severity == 'Light':
            weight = 2
            
        adjusted_weight = weight / (num_first_course_sections * num_second_course_sections)
        
        adjusted_severity = 'L'
        if adjusted_weight > 2 and adjusted_weight <= 6:
            adjusted_severity = 'M'
        elif adjusted_weight > 6:
            adjusted_severity = 'H'
        
        # Enter each first course-second course combination into the list
        if first_course < second_course:
            t = (first_course, second_course, adjusted_severity, adjusted_weight)
        else:
            t = (second_course, first_course, adjusted_severity, adjusted_weight)

        if t not in conflicts:
            conflicts.append(t)
            
    print conflicts
    
    # Build the edges of the graph model
    edges = solver.build_edges(vertices, conflicts)
    
    # Calculate overlaps and gaps for each pair of timeslots
    overlapping_timeslots, timeslot_gaps = solver.calculate_overlapping_timeslots_and_gaps(timeslots_with_ids)

    # Call the one-pass scheduler
    solution = solver.one_pass_solver(vertices, edges, overlapping_timeslots, timeslot_gaps)
    
    # Enter the assigned timeslot/room for each section into the database
    for c in solution:
        result = solution[c]

        # Convert timeslot id into its 24-hour string representation
        if result['assigned_timeslot'] != None:
            timeslot_string = timeslots_24_hour[result['assigned_timeslot']]
        else:
            timeslot_string = 'None'
        
        original_name = transformed_to_original_names_map[c]
        s = Section.query.filter_by(section_name = original_name).first();
        s.assigned_timeslot = timeslot_string
        
        if s.assigned_timeslot == 'None':
            s.assigned_room = 'None'
        else:
            s.assigned_room = result['assigned_room'].replace('_', ' ')
        
    # Commit changes
    db.session.commit()

    return "null"
    
    
#--- Main
app.debug = True

if __name__ == '__main__':
    app.run(host=os.getenv('IP', '0.0.0.0'), port=int(os.getenv('PORT', 8080)))