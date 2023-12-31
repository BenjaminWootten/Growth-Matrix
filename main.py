from designer import *
import numpy as np
import math as m
from dataclasses import dataclass
from levels import change_level

@dataclass
class Box:
    # Represents a box in 3d space, comprised of both data and DesignerObjects
    color: str
    size: list[float] # [x,y,z]
    center: list[float] # [x,y,z]
    points: list[list[float]] # [[x,y,z]]
    projected_points: list[list[float]] # [[x,y]]
    vertices: list[DesignerObject]
    lines: list[DesignerObject]
    faces: list[DesignerObject]
    is_moving: bool
    movement: list[float] # [x,y,z]

@dataclass
class Button:
    # A button the player can click to navigate the menus
    background: DesignerObject
    border: DesignerObject
    text: DesignerObject
    color: str

@dataclass
class World:
    # Contains all information about the 3d world at a given time
    base: Box
    boxes: list[list[Box]] # [[Red], [White], [Blue], [Green]]
    box_render_order: list[Box]
    angle: list[float] # [x, y, z]
    pan_pos: list[int]
    is_panning: bool
    is_clicking_interactable: bool
    scaled_up_red_box: Box
    previously_scaled_up_red_box: Box
    is_scaling: bool
    buttons: list[Button]

@dataclass
class MainMenu:
    # Contains Main Menu elements
    title: DesignerObject
    title_background: DesignerObject
    title_border: DesignerObject
    play_button: Button
    instructions_button: Button

@dataclass
class InstructionsMenu:
    # Contains Instructions Menu elements
    background: DesignerObject
    border: DesignerObject
    text: list[DesignerObject]
    close_button: Button
    title: DesignerObject
    title_background: DesignerObject
    title_border: DesignerObject

@dataclass
class LevelMenu:
    # Contains Levels Menu elements
    title: DesignerObject
    title_background: DesignerObject
    title_border: DesignerObject
    level_buttons: list[Button]
    back_button: Button

# Constants
TOTAL_LEVELS = 10
CENTER = [get_width()/2, get_height()/2]
SCALE = 50.0 # Scale for rendering
SCALE_MAX = 3.0 # Max size of red boxes
SCALE_SPEED = 0.2 # Scale speed of red boxes

PROJECTION_MATRIX = np.matrix([
    [1, 0, 0],
    [0, 1, 0]
])

# Global variables persist between world resets when loading levels
level_number = 0
completed_levels = []
for i in range(0, TOTAL_LEVELS):
    completed_levels.append(False)

def create_button(message: str, x: int, y: int, color: str) -> Button:
    '''
    This function creates a button instance to be used in UI elements

    Args:
        message (str): the text on the button
        x (int): the x position of the button
        y (int): the y position of the button
        color (str): the color of the button

    Returns:
        Button: a button instance based on the arguments
    '''
    x_padding = 4
    y_padding = 2
    button_text = text("black", message, 20, x, y)
    border = rectangle("white", button_text.width + 2 * x_padding, button_text.height + 2 * y_padding, x, y)
    background = rectangle(color, button_text.width + x_padding, button_text.height + y_padding, x, y)
    button_text = text("black", message, 20, x, y)
    return Button(background, border, button_text, color)

def button_hover(button: Button) -> bool:
    '''
    This function checks if a button is being touched by the mouse and changes the color of it accordingly to create a
    hovering effect. This works for both gray and green buttons

    Args:
        button (Button): The button to be checked

    Returns:
        bool: returns True if the mouse is hovering over the button, else returns False
    '''
    if colliding_with_mouse(button.border):
        button.background.color = button.color
        return True
    else:
        if button.color == "gray":
            button.background.color = "darkgray"
        else:
            button.background.color = "lightgreen"
        return False

def check_game_button_press(world: World):
    '''
    This function checks if a button in the game scene has been pressed and changes the scene based on which of the 2
    buttons (level menu and reset level) has been pressed.

    Args:
        world (World): the current world data

    Returns:
        None
    '''
    for button in world.buttons:
        if button_hover(button):

                if button.text.x < CENTER[0]:
                    # Menu Button
                    change_scene('level_menu')
                else:
                    # Reset Button
                    change_scene('game')

def generate_points(size: list[float], position: list[float]) -> list[[]]:
    '''
    This function generates a set of 3d coordinates representing the 8 vertices of a box

    Args:
        size (list[float]): a list of 3 floats representing the x, y, and z sizes of the box
        position (list[float]): a list of 3 floats representing the x, y, and z positions of the box

    Returns:
        list[[]]: A list of 8 3x1 NumPy matrices, representing the x, y, and z position of the 8 vertices
    '''
    points = []
    xpos = position[0]
    ypos = position[1]
    zpos = position[2]
    xsize = size[0]
    ysize = size[1]
    zsize = size[2]
    #top 4 points
    points.append(np.matrix([xpos - xsize / 2, ypos - ysize / 2, zpos + zsize / 2]))
    points.append(np.matrix([xpos + xsize / 2, ypos - ysize / 2, zpos + zsize / 2]))
    points.append(np.matrix([xpos + xsize / 2, ypos + ysize / 2, zpos + zsize / 2]))
    points.append(np.matrix([xpos - xsize / 2, ypos + ysize / 2, zpos + zsize / 2]))
    # bottom 4 points
    points.append(np.matrix([xpos - xsize / 2, ypos - ysize / 2, zpos - zsize / 2]))
    points.append(np.matrix([xpos + xsize / 2, ypos - ysize / 2, zpos - zsize / 2]))
    points.append(np.matrix([xpos + xsize / 2, ypos + ysize / 2, zpos - zsize / 2]))
    points.append(np.matrix([xpos - xsize / 2, ypos + ysize / 2, zpos - zsize / 2]))

    return points

def scale_points(box: Box, scale: list[float]):
    '''
    This function scales the given box by the given amount

    Args:
        box (Box): the box object to be scaled
        scale (float): the amount to scale the box by

    Returns:
        None
    '''
    box.size[0] += scale[0]
    box.size[1] += scale[1]
    box.size[2] += scale[2]
    box.center[1] -= scale[1]/2

def create_line(i: int, j: int, points: list[[]]) -> DesignerObject:
    '''
    This function draws a line in the viewport, making up one edge of a box, based on the list of 2d coordinates and
    2 indexes given

    Args:
        i (int): the index in the list of the first point of the line
        j (int): the index in the list of the second point of the line
        points (list[[]]): the list of 2d coordinates representing a projected cube to be used for drawing lines

    Returns:
        DesignerObject: The line object generated from the list and indexes
    '''
    # Returns a line connecting points at indexes i and j in list points
    return line("black", points[i][0], points[i][1], points[j][0], points[j][1])

def create_face(color: str, i: int, j: int, k: int, l: int, points: list[[]]) -> DesignerObject:
    '''
    This function draws a shape in the viewport, making up one face of a box, based on the list of 2d coordinates
    and 2 indexes given

    Args:
        i (int): the index in the list of the first vertex of the shape
        j (int): the index in the list of the second vertex of the shape
        k (int): the index in the list of the third vertex of the shape
        l (int): the index in the list of the fourth vertex of the shape
        points (list[[]]): the list of 2d coordinates representing a projected cube to be used for drawing shapes

    Returns:
        DesignerObject: The shape object generated from the list and indexes
    '''
    # Returns a shape of chosen color connecting points at indexes i, j, k, and l in list points
    return shape(color, [points[i][0], points[i][1], points[j][0], points[j][1], points[k][0], points[k][1],
                         points[l][0], points[l][1]], absolute=True, anchor='topleft')

def create_box(size: list[float], position: list[float], type: str) -> Box:
    '''
    This function generates a box object of the given size, position, and type

    Args:
        size (list[float]): a list containing the x, y, and z sizes of the box
        position (list[float]): a list containing the x, y, and z positions of the box
        type (str): can be either "base", "white", "red", "blue", or "green", which correspond to the color and
        behavior of the box

    Returns:
        Box: the box object generated from the inputs
    '''
    # Returns a box of given type, size, and center position

    projected_points = []
    vertices = []
    lines = []
    faces = []

    if type == "base":
        type = "white"

    points = generate_points(size, position)

    for point in points:
        # @ is the matrix multiplication operator
        # Use transpose to change point from 1x3 to 3x1 matrix to make multiplication with 2d matrix compatible
        projected2d = PROJECTION_MATRIX @ point.transpose()

        # Set x and y to projected position
        x = projected2d[0, 0] * SCALE + CENTER[0]
        y = projected2d[1, 0] * SCALE + CENTER[1]

        # Add 8 circles representing the vertices
        vertices.append(circle("black", 5, x, y))

        # Add the coordinates of the projected position to projected_points
        projected_points.append([x, y])

    # Add 12 lines outlining cube to list lines
    for p in range(4):
        lines.append(create_line(p, (p + 1) % 4, projected_points))
        lines.append(create_line(p + 4, (p + 1) % 4 + 4, projected_points))
        lines.append(create_line(p, p + 4, projected_points))

    faces.append(create_face(type, 0, 1, 2, 3, projected_points))
    faces.append(create_face(type, 4, 5, 6, 7, projected_points))
    for p in range(4):
        faces.append(create_face(type, p, (p + 1) % 4, (p + 1) % 4 + 4, p + 4, projected_points))

    return Box(type, size, position, points, projected_points, vertices, lines, faces, False,
               [0.0, 0.0, 0.0])

def destroy_box(box: Box):
    '''
    This function destroys a box's rendered DesignerObjects, but not its data. This allows all the
    DesignerObjects to be regenerated based on updated data

    Args:
        box (Box): the box to be destroyed

    Returns:
        None
    '''
    for vertex in box.vertices:
        destroy(vertex)
    for line in box.lines:
        destroy(line)
    for face in box.faces:
        destroy(face)

def draw_box(angle: list[float], box: Box):
    '''
        This function updated the given box based on new size, position, and world rotation.

        Args:
            angle (list[float]): the current x, y, and z angle of all objects in the world
            box (Box): the box to be updated

        Returns:
            None
        '''
    rotation_x_matrix = np.matrix([
        [1, 0, 0],
        [0, m.cos(angle[0]), -m.sin(angle[0])],
        [0, m.sin(angle[0]), m.cos(angle[0])]
    ])

    rotation_y_matrix = np.matrix([
        [m.cos(angle[1]), 0, m.sin(angle[1])],
        [0, 1, 0],
        [-m.sin(angle[1]), 0, m.cos(angle[1])]
    ])

    rotation_z_matrix = np.matrix([
        [m.cos(angle[2]), -m.sin(angle[2]), 0],
        [m.sin(angle[2]), m.cos(angle[2]), 0],
        [0, 0, 1]
    ])

    destroy_box(box)

    box.points.clear()
    box.points = generate_points(box.size, box.center)

    # Calculating rotation and projection
    for index, point in enumerate(box.points):
        # @ is the matrix multiplication operator
        # Use transpose to change point from 1x3 to 3x1 matrix to make multiplication with 2d matrix compatible

        # For each 3d coordinate, multiply by rotation_z to rotate points about the z axis
        rotated2d = rotation_x_matrix @ point.transpose()
        rotated2d = rotation_y_matrix @ rotated2d
        rotated2d = rotation_z_matrix @ rotated2d
        # For each 3d coordinate, multiply by projection_matrix to convert to 2d coordinate
        projected2d = PROJECTION_MATRIX @ rotated2d

        # Set projected x and y values for each coordinate
        x = projected2d[0, 0] * SCALE + CENTER[0]
        y = projected2d[1, 0] * SCALE + CENTER[1]

        # Add x and y values to list of projected points
        box.projected_points[index] = [x, y]

        # Move corresponding vertices to newly calculated positions
        box.vertices[index].x = x
        box.vertices[index].y = y


    # Reloading box geometry
    # Generates 6 new faces
    box.faces[0] = create_face(box.color, 0, 1, 2, 3, box.projected_points)
    box.faces[1] = create_face(box.color, 4, 5, 6, 7, box.projected_points)
    for p in range(4):
        box.faces[p + 2] = create_face(box.color, p, (p + 1) % 4, (p + 1) % 4 + 4, p + 4, box.projected_points)\

    # Generates 12 new lines
    for p in range(4):
        box.lines[p] = create_line(p, (p + 1) % 4, box.projected_points)
        box.lines[p + 4] = create_line(p + 4, (p + 1) % 4 + 4, box.projected_points)
        box.lines[p + 8] = create_line(p, p + 4, box.projected_points)

    # Generates 8 new vertices
    for index, projected_point in enumerate(box.projected_points):
        box.vertices[index] = circle("black", 5, projected_point[0], projected_point[1])

def main(world: World):
    '''
    This function serves as the main game loops and is run every frame on the game scene. It performs most game
    operations: rendering, panning, scaling and pushing boxes, and updating button hovering.

    Args:
        world (World): the current world data

    Returns:
        None
    '''

    calculate_render_order(world)



    # Rotating boxes with mouse pan
    if world.is_panning:
        pan_world(world)

    # render all boxes
    for box in world.box_render_order:
        draw_box(world.angle, box)

    if world.is_scaling:
        directions = [True, True, True]
        directions[0] = (check_box_collision(world, world.scaled_up_red_box, 0, 1) and
                         check_box_collision(world, world.scaled_up_red_box, 0, -1))
        directions[2] = (check_box_collision(world, world.scaled_up_red_box, 2, 1) and
                         check_box_collision(world, world.scaled_up_red_box, 2, -1))

        move_blue_box(world, world.scaled_up_red_box)

        scale_red_box(world, directions)


    for button in world.buttons:
        button_hover(button)

def calculate_render_order(world: World):
    '''
    This function orders all boxes in the world in a list based on their position relative to the camera, assuring they
    are rendered in the correct order

    Args:
        world (World): the current world data

    Returns:
        None
    '''
    # Clear render order so it can be recalculated
    world.box_render_order.clear()

    for type in world.boxes:
        # Run through all 4 box types

        for box in type:
            # This loop adds all boxes to a new list insertion sorted from furthest to closest to the camera,
            # therefore preventing layering issues upon rendering

            i = 0

            # When y rotation is between 45 degrees and 135 degrees, render from smallest x to largest x
            if (m.pi * 2 / 8) <= world.angle[1] % (m.pi * 2) < (m.pi * 2 / 8) * 3:
                for render_box in world.box_render_order:
                    if box.center[0] > render_box.center[0]:
                        i += 1
                    # If 2 boxes have the same x, check if rotation is greater than or less than 90 degrees and render
                    # based on z value
                    elif box.center[0] == render_box.center[0]:
                        if world.angle[1] % (m.pi * 2) > (m.pi * 2 / 8) * 2:
                            if box.center[2] > render_box.center[2]:
                                i += 1
                        else:
                            if box.center[2] < render_box.center[2]:
                                i += 1

            # When y rotation is between 135 degrees and 225 degrees, render from smallest z to largest z
            if (m.pi * 2 / 8) * 3 <= world.angle[1] % (m.pi * 2) < (m.pi * 2 / 8) * 5:
                for render_box in world.box_render_order:
                    if box.center[2] > render_box.center[2]:
                        i += 1
                    # If 2 boxes have the same z, check if rotation is greater than or less than 180 degrees and render
                    # based on x value
                    elif box.center[2] == render_box.center[2]:
                        if world.angle[1] % (m.pi * 2) > (m.pi * 2 / 8) * 4:
                            if box.center[0] < render_box.center[0]:
                                i += 1
                        else:
                            if box.center[0] > render_box.center[0]:
                                i += 1

            # When y rotation is between 225 degrees and 315 degrees, render from largest x to smallest x
            if (m.pi * 2 / 8) * 5 <= world.angle[1] % (m.pi * 2) < (m.pi * 2 / 8) * 7:
                for render_box in world.box_render_order:
                    if box.center[0] < render_box.center[0]:
                        i += 1
                    # If 2 boxes have the same x, check if rotation is greater than or less than 270 degrees and render
                    # based on z value
                    elif box.center[0] == render_box.center[0]:
                        if world.angle[1] % (m.pi * 2) > (m.pi * 2 / 8) * 6:
                            if box.center[2] < render_box.center[2]:
                                i += 1
                        else:
                            if box.center[2] > render_box.center[2]:
                                i += 1

            # When y rotation is greater than 315 degrees or fewer than 45 degrees, render from largest z to smallest z
            if (m.pi * 2 / 8) * 7 <= world.angle[1] % (m.pi * 2) or world.angle[1] % (m.pi * 2) < (m.pi * 2 / 8):
                for render_box in world.box_render_order:
                    if box.center[2] < render_box.center[2]:
                        i += 1
                    # If 2 boxes have the same z, check if rotation is less than 45 degrees or greater than 315 degrees
                    # and render based on x value
                    elif box.center[2] == render_box.center[2]:
                        if world.angle[1] % (m.pi * 2) < (m.pi / 2):
                            if box.center[0] > render_box.center[0]:
                                i += 1
                        else:
                            if box.center[0] < render_box.center[0]:
                                i += 1

            world.box_render_order.insert(i, box)

    # Rendering level base before or after cubes based on x rotation
    if world.angle[0] % (m.pi * 2) > m.pi and (
            world.angle[1] % (m.pi * 2) <= (m.pi / 2) or world.angle[1] % (m.pi * 2) > (m.pi * 3 / 2)):
        world.box_render_order.append(world.base)
    elif world.angle[0] % (m.pi * 2) < m.pi and ((m.pi / 2) < world.angle[1] % (m.pi * 2) < (m.pi * 3 / 2)):
        world.box_render_order.append(world.base)
    else:
        world.box_render_order.insert(0, world.base)

def red_box_interaction(world: World):
    '''
    This function is run when clicking and determines if the player has clicked on a red box and if it can be scaled
    up or not.

    Args:
        world (World): the current world data

    Returns:
        None
    '''
    # Creates a list containing all boxes colliding with the mouse upon clicking
    boxes_clicked = []
    for type in world.boxes:
        for box in type:
            for face in box.faces:
                if colliding_with_mouse(face):
                    boxes_clicked.append(box)

    # Checks if any boxes were clicked as a safeguard
    if boxes_clicked:
        # Calculates which of all clicked boxes is the closest to the camera using world.box_render_order
        closest_clicked = boxes_clicked[0]
        for box in world.box_render_order:
            for box_clicked in boxes_clicked:
                if box == box_clicked:
                    closest_clicked = box_clicked

        # Checks if the closest clicked box is red
        if closest_clicked.color == "red" and not world.is_scaling:
            world.is_clicking_interactable = True
            if closest_clicked.size[1] == 1.0 and closest_clicked != world.scaled_up_red_box:
                world.previously_scaled_up_red_box = world.scaled_up_red_box
                world.scaled_up_red_box = closest_clicked
                world.is_scaling = True
            else:
                world.is_clicking_interactable = False

    else:
        world.is_clicking_interactable = False

    boxes_clicked.clear()

def scale_red_box(world: World, directions: list[bool]):
    '''
    This function scales up a red box when it is clicked and scales down the previously scaled up red box.

    Args:
        world (World): the current world data
        directions (list[bool]): a list of 3 bools indicating if the box can be scaled in the x, y, and z directions

    Returns:
        None
    '''
    scale_speed = [0,SCALE_SPEED,0]
    if directions[0]:
        scale_speed[0] = SCALE_SPEED
    if directions[2]:
        scale_speed[2] = SCALE_SPEED


    # Scales up red box when it is clicked and not already scaled
    if world.scaled_up_red_box:
        if world.scaled_up_red_box.size[1] < SCALE_MAX:

            scale_points(world.scaled_up_red_box, scale_speed)

            # Checks if there is a red box currently scaled up and scales it down
            if world.previously_scaled_up_red_box:
                scale_down_speed = [0,0,0]
                if world.previously_scaled_up_red_box.size[0] > 1.0:
                    scale_down_speed[0] = -SCALE_SPEED
                if world.previously_scaled_up_red_box.size[1] > 1.0:
                    scale_down_speed[1] = -SCALE_SPEED
                if world.previously_scaled_up_red_box.size[2] > 1.0:
                    scale_down_speed[2] = -SCALE_SPEED
                scale_points(world.previously_scaled_up_red_box, scale_down_speed)
        else:
            world.is_scaling = False

def move_blue_box(world: World, pushing_box: Box):
    '''
    This function moves a blue box if there is a red box next to it being scaled up or if there is a blue box pushing it

    Args:
        world (World): the current world data
        pushing_box (Box): this can be either a growing red box or a moving blue box and the movement behavior changes
        slightly based on that

    Returns:
        None
    '''
    for blue_box in world.boxes[2]: # 2 is blue boxes
        if not blue_box.is_moving:
            blue_box.color = "blue"
            if pushing_box.color == "red":

                if pushing_box.center[0] == blue_box.center[0] and pushing_box.size[2] > 1.0:
                    if pushing_box.center[2] == blue_box.center[2] - 1:
                        blue_box.is_moving = True
                        blue_box.movement[2] = SCALE_SPEED/2
                    elif pushing_box.center[2] == blue_box.center[2] + 1:
                        blue_box.is_moving = True
                        blue_box.movement[2] = -SCALE_SPEED/2

                elif pushing_box.center[2] == blue_box.center[2] and pushing_box.size[0] > 1.0:
                    if pushing_box.center[0] == blue_box.center[0] - 1:
                        blue_box.is_moving = True
                        blue_box.movement[0] = SCALE_SPEED/2
                    elif pushing_box.center[0] == blue_box.center[0] + 1:
                        blue_box.is_moving = True
                        blue_box.movement[0] = -SCALE_SPEED/2

            elif pushing_box.color == "blue":
                if round(pushing_box.center[0]) == blue_box.center[0]:
                    if (round(pushing_box.center[2]) == blue_box.center[2] - 1 or
                            round(pushing_box.center[2]) == blue_box.center[2] + 1):
                        blue_box.is_moving = True
                        blue_box.movement[2] = pushing_box.movement[2]
                if round(pushing_box.center[2]) == blue_box.center[2]:
                    if (round(pushing_box.center[0]) == blue_box.center[0] - 1 or
                            round(pushing_box.center[0]) == blue_box.center[0] + 1):
                        blue_box.is_moving = True
                        blue_box.movement[0] = pushing_box.movement[0]

            if blue_box.is_moving:
                move_blue_box(world, blue_box)

        else:
            blue_box.center[0] += blue_box.movement[0]
            blue_box.center[2] += blue_box.movement[2]
            if pushing_box.size[1] >= SCALE_MAX or (pushing_box.color == "blue" and pushing_box.is_moving == False):
                blue_box.is_moving = False
                blue_box.movement = [0, 0, 0]
                blue_box.center[0] = round(blue_box.center[0])
                blue_box.center[2] = round(blue_box.center[2])

def check_box_collision(world: World, checked_box: Box, axis: int, direction: int) -> bool:
    '''
    This function determines if a red box can be scaled up in the given direction by checking if there is a white or red
    box adjacent in the given direction, or if there is a blue box it will check the next space via recursion until
    there is either a white box, red box, or no box.

    Args:
        world (World): the current world data
        checked_box (Box): the box having its adjacent collisions being checked
        axis (int): the axis along which the check is performed, 0 represents x and 2 represents z
        direction (int): the direction within the axis in which the check is performed, 1 for positive and -1 for
            negative

    Returns:
        bool: True if there are no collisions, False if there is one
    '''
    # Run through all boxes in the world and filter out any that aren't white or blue
    other_axis = 0
    if axis == 0:
        other_axis = 2

    for index, type in enumerate(world.boxes):
        if index == 1 or index == 2 or index == 0: # 1 is white, 2 is blue, 0 is red
            for box in type:
                if (checked_box.center[axis] == box.center[axis] + direction and
                        checked_box.center[other_axis] == box.center[other_axis]):
                    #Check if a blue, red,  or white box is directly next to the box we are checking along the given
                    #axis and direction, which is either 1 or -1
                    if box.color == "white" or box.color == "red":
                        # If the neighboring box is white or red, return false
                        return False
                    else:
                        # If the neighboring box is blue, check if it has a white box in the next space over
                        return check_box_collision(world, box, axis, direction)
    return True

def pan_start(world: World, x: float, y: float):
    '''
    This function runs when the player does not click a red box and initiates a pan

    Args:
        world (World): the current world data
        x (float): the x position of the click
        y (float): the y position of the click

    Returns:
        None
    '''
    if not world.is_clicking_interactable:
        world.pan_pos = [x, y]
        world.is_panning = True

def pan_world(world: World):
    '''
    This function pans the world while the player holds down the mouse button

    Args:
        world (World): the current world data

    Returns:
        None
    '''
    world.angle[1] -= (get_mouse_x() - world.pan_pos[0]) / 500

    if world.angle[1] % (m.pi * 2) < (m.pi / 2) or world.angle[1] % (m.pi * 2) >= (m.pi * 3 / 2):
        world.angle[0] += (get_mouse_y() - world.pan_pos[1]) / 500
    elif world.angle[1] % (m.pi * 2) >= (m.pi / 2) and world.angle[1] % (m.pi * 2) < (m.pi * 3 / 2):
        world.angle[0] -= (get_mouse_y() - world.pan_pos[1]) / 500

    world.pan_pos[0] = get_mouse_x()
    world.pan_pos[1] = get_mouse_y()

def pan_end(world: World):
    '''
    This function ends a pan when the player releases the mouse button

    Args:
        world (World): the current world data

    Returns:
        None
    '''
    world.is_panning = False

def detect_win(world: World) -> bool:
    '''
    This function checks if all green boxes have been filled with blue boxes and returns the result

    Args:
        world (World): the current world data

    Returns:
        bool: returns True if all green boxes are filled, and False otherwise
    '''
    green_boxes_filled = []
    for green_box in world.boxes[3]: # 3 is green boxes
        for blue_box in world.boxes[2]: # 2 is blue boxes
            if blue_box.center == green_box.center:
                green_boxes_filled.append(True)
                blue_box.color = "purple"

    return len(green_boxes_filled) == len(world.boxes[3])

def end_level(world: World):
    '''
    This function ends the level and changes the scene to level_menu if detect_win returns True

    Args:
        world (World): the current world data

    Returns:
        None
    '''
    if detect_win(world):
        global completed_levels
        completed_levels[level_number] = True
        change_scene('level_menu')

def create_level(level: list[list[str]], base_x, base_z) -> World:
    '''
    This function converts a 2d list of strings representing boxes in a level into level data and returns a World based
    on that.

    Args:
        level (list[list[str]]): the 2d list of strings to be converted to a World
        base_x (int): the x width of the base of the level
        base_z (int): the z width of the base of the level

    Returns:
        World: the created world
    '''
    #   = empty
    # r = red
    # w = white
    # b = blue
    # g = green
    base = create_box([base_x, 1, base_z], [0,1,0], "base")
    red = []
    white = []
    blue = []
    green = []
    for i, row in enumerate(reversed(level)):
        for j, character in enumerate(row):
            if character == "r":
                red.append(create_box([1,1,1], [j-m.floor(base_x/2), 0, i-m.floor(base_z/2)],
                                      "red"))
            elif character == "w":
                white.append(create_box([1, 1, 1], [j-m.floor(base_x/2), 0, i-m.floor(base_z/2)],
                                        "white"))
            elif character == "b":
                blue.append(create_box([1, 1, 1], [j-m.floor(base_x/2), 0, i-m.floor(base_z/2)],
                                       "blue"))
            elif character == "g":
                green.append(create_box([1, 1, 1], [j-m.floor(base_x/2), 0, i-m.floor(base_z/2)],
                                        "green"))
    return World(base, [red, white, blue, green], [], [0.3, 0.3, 0.0], [0, 0], False, False, None, None, False, [
        create_button("Reset Level", get_width()-50, get_height()-20, "gray"),
        create_button("Level Select", 50, get_height()-20, "gray")
    ])

def create_world() -> World:
    '''
    This function creates the world by passing the current level number into the create_level function

    Args:
        None

    Returns:
        World: the created world
    '''
    set_window_color("black")

    return create_level(change_level(level_number), 9, 9)

def create_main_menu() -> MainMenu:
    '''
    This function creates the main menu

    Args:
        None

    Returns:
        MainMenu: the created menu
    '''
    set_window_color("black")

    x_padding = 10
    y_padding = 10

    title = text("black", "Growth Matrix", 50, CENTER[0], CENTER[1]/3)
    title_border = rectangle("white", title.width + 2*x_padding, title.height + 2*y_padding, CENTER[0],
                             CENTER[1]/3)
    title_background = rectangle("lightslategray", title.width + x_padding, title.height + y_padding, CENTER[0],
                                 CENTER[1]/3)
    title = text("black", "Growth Matrix", 50, CENTER[0], CENTER[1] / 3)
    play_button = create_button("     Play     ", CENTER[0], CENTER[1] * 1.1, "gray")
    instructions_button = create_button("Instructions", CENTER[0], CENTER[1] *1.1 + 40, "gray")

    return MainMenu(title, title_background, title_border, play_button, instructions_button)

def main_menu_button_hover(menu: MainMenu):
    '''
    This function updates the color of the buttons on the main menu if the player hovers over them

    Args:
        menu (MainMenu): the main menu

    Returns:
        None
    '''
    button_hover(menu.play_button)
    button_hover(menu.instructions_button)

def main_menu_click(menu: MainMenu):
    '''
    This function registers clicks on the main menu buttons and changes to the corresponding menu

    Args:
        menu (MainMenu): the main menu

    Returns:
        None
    '''
    if button_hover(menu.play_button):
        change_scene('level_menu')
    if button_hover(menu.instructions_button):
        push_scene('instructions_menu')

def create_instructions_menu() -> InstructionsMenu:
    '''
    This function creates the instructions menu

    Args:
        None

    Returns:
        InstructionsMenu: the created instructions menu
    '''
    width = 600
    height = 250
    x_padding = 10
    y_padding = 10
    border = rectangle("white", width + 5, height + 5, CENTER[0], CENTER[1])
    background = rectangle("dimgray", width, height, CENTER[0], CENTER[1])
    instructions = [
        text("black", "The matrix can be panned around by clicking and dragging the mouse.",
             20, CENTER[0], CENTER[1]-height/2+25),
        text("black", "Red boxes can be grown by clicking on them.",
             20, CENTER[0], CENTER[1]-height/2+50),
        text("black", "Only one Red box can be grown at a time.",
             20, CENTER[0], CENTER[1]-height/2+75),
        text("black", "Blue boxes can be pushed by growing Red boxes or by other Blue boxes.",
             20, CENTER[0], CENTER[1]-height/2+100),
        text("black", "White boxes can block the growth of Red boxes in one or two directions.",
             20, CENTER[0], CENTER[1]-height/2+125),
        text("black", "To complete each matrix all Green boxes must be filled in with Blue boxes.",
             20, CENTER[0], CENTER[1]-height/2+150),
        text("black", "Filled Green boxes will turn Purple.",
             20, CENTER[0], CENTER[1]-height/2+175)
    ]

    close_button = create_button("Close", CENTER[0], CENTER[1]+height/2-25, "gray")
    title = text("black", "Growth Matrix", 50, CENTER[0], CENTER[1] / 3)
    title_border = rectangle("white", title.width + 2 * x_padding, title.height + 2 * y_padding, CENTER[0],
                             CENTER[1] / 3)
    title_background = rectangle("lightslategray", title.width + x_padding, title.height + y_padding, CENTER[0],
                                 CENTER[1] / 3)
    title = text("black", "Growth Matrix", 50, CENTER[0], CENTER[1] / 3)
    return InstructionsMenu(background, border, instructions, close_button, title, title_border, title_background)

def instructions_menu_hover(menu: InstructionsMenu):
    '''
    This function updates the color of the buttons on the instructions menu if the player hovers over them

    Args:
        menu (InstructionsMenu): the instructions menu

    Returns:
        None
    '''
    button_hover(menu.close_button)

def instructions_menu_click(menu: InstructionsMenu):
    '''
    This function registers clicks on the instructions menu buttons and changes to the corresponding menu

    Args:
        menu (InstructionsMenu): the instructions menu

    Returns:
        None
    '''
    if button_hover(menu.close_button):
        pop_scene()

def create_level_menu() -> LevelMenu:
    '''
    This function creates the level menu based on the number of levels there are and changes the color of the buttons
    to green if a level has been completed. It also displays a victory message if all levels have been completed.

    Args:
        None

    Returns:
        LevelMenu: the created menu
    '''
    x_padding = 10
    y_padding = 10

    level_buttons = []
    all_completed = True
    for i in range(0, TOTAL_LEVELS):
        if completed_levels[i]:
            color = "green"
        else:
            color = "gray"
            all_completed = False
        level_buttons.append(create_button("  " + str(i+1) + "  ", i * 50 + 100, CENTER[1], color))

    if not all_completed:
        message = " Levels "
    else:
        message = "    Congratulations! :)    "

    title = text("black", message, 40, CENTER[0], CENTER[1] / 2)

    back_button = create_button("   back   ", 50, get_height()-20, "gray")

    title_border = rectangle("white", title.width + 2 * x_padding, title.height + 2 * y_padding, CENTER[0],
                             CENTER[1] / 3)
    title_background = rectangle("lightslategray", title.width + x_padding, title.height + y_padding, CENTER[0],
                                 CENTER[1] / 3)

    title = text("black", message, 50, CENTER[0], CENTER[1] / 3)

    return LevelMenu(title, title_border, title_background, level_buttons, back_button)

def level_menu_button_hover(menu: LevelMenu):
    '''
    This function updates the color of the buttons on the level menu if the player hovers over them

    Args:
        menu (LevelMenu): the instructions menu

    Returns:
        None
    '''
    for button in menu.level_buttons:
        button_hover(button)
    button_hover(menu.back_button)

def level_menu_click(menu: LevelMenu):
    '''
    This function registers clicks on the level menu buttons and changes to the corresponding menu or level

    Args:
        menu (LevelMenu): the instructions menu

    Returns:
        None
    '''
    if button_hover(menu.back_button):
        change_scene('main_menu')

    for i, button in enumerate(menu.level_buttons):
        if button_hover(button):
            global level_number
            level_number = i
            change_scene('game')


# Main menu events
when('starting: main_menu', create_main_menu)
when('updating: main_menu', main_menu_button_hover)
when('clicking: main_menu', main_menu_click)

# Instructions menu events
when('starting: instructions_menu', create_instructions_menu)
when('updating: instructions_menu', instructions_menu_hover)
when('clicking: instructions_menu', instructions_menu_click)

# Level select menu events
when('starting: level_menu', create_level_menu)
when('updating: level_menu', level_menu_button_hover)
when('clicking: level_menu', level_menu_click)


# Game events
when('starting: game', create_world)

when('clicking: game', red_box_interaction)
when('input.mouse.down: game', check_game_button_press)
when('input.mouse.down: game', pan_start)
when('input.mouse.up: game', pan_end)

when('updating: game', end_level)
when('updating: game', main)

start(scene='main_menu')