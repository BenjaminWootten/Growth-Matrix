from designer import *
import numpy as np
import math as m
from dataclasses import dataclass

@dataclass
class Box:
    color: str
    scale: float
    points: list[list[float]]
    projected_points: list[list[float]]
    vertices: list[DesignerObject]
    lines: list[DesignerObject]
    faces: list[DesignerObject]


@dataclass
class World:
    boxes: list[list[Box]] # [[Base], [White], [Red], [Blue], [Green]]
    angle: list[float] # [x, y, z]
    click_pos: list[int]
    is_clicking: bool


CENTER = [get_width()/2, get_height()/2]

PROJECTION_MATRIX = np.matrix([
    [1, 0, 0],
    [0, 1, 0]
])


def generate_points(size: list[float], position: list[float]) -> list[[]]:
    # Returns a list of points representing a box based on the given xyz size and xyz position
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

def create_line(i: int, j: int, points) -> DesignerObject:
    # Returns a line connecting points at indexes i and j in list points
    return line("black", points[i][0], points[i][1], points[j][0], points[j][1])

def create_face(color: str, i: int, j: int, k: int, l: int, points) -> DesignerObject:
    # Returns a shape of chosen color connecting points at indexes i, j, k, and l in list points
    return shape(color, [points[i][0], points[i][1], points[j][0], points[j][1], points[k][0], points[k][1], points[l][0], points[l][1]], absolute=True, anchor='topleft')


def create_box(size: list[float], position: list[float], type: str) -> Box:
    # Returns a box of given type, size, and center position

    starting_scale = 50.0
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
        x = projected2d[0, 0] * starting_scale + CENTER[0]
        y = projected2d[1, 0] * starting_scale + CENTER[1]

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

    return Box(type, starting_scale, points, projected_points, vertices, lines, faces)

def destroy_box(box: Box):
    for vertex in box.vertices:
        destroy(vertex)
    for line in box.lines:
        destroy(line)
    for face in box.faces:
        destroy(face)

def update_boxes(world: World):

    rotation_x_matrix = np.matrix([
        [1, 0, 0],
        [0, m.cos(world.angle[0]), -m.sin(world.angle[0])],
        [0, m.sin(world.angle[0]), m.cos(world.angle[0])]
    ])

    rotation_y_matrix = np.matrix([
        [m.cos(world.angle[1]), 0, m.sin(world.angle[1])],
        [0, 1, 0],
        [-m.sin(world.angle[1]), 0, m.cos(world.angle[1])]
    ])

    rotation_z_matrix = np.matrix([
        [m.cos(world.angle[2]), -m.sin(world.angle[2]), 0],
        [m.sin(world.angle[2]), m.cos(world.angle[2]), 0],
        [0, 0, 1]
    ])

    for type in world.boxes:
        # Run through all 5 box types
        for box in type:
            # Update each box in each type

            destroy_box(box)

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
                x = projected2d[0, 0] * box.scale + CENTER[0]
                y = projected2d[1, 0] * box.scale + CENTER[1]

                # Add x and y values to list of projected points
                box.projected_points[index] = [x, y]

                # Move corresponding vertices to newly calculated positions
                box.vertices[index].x = x
                box.vertices[index].y = y

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

            # Code for rotating box with mouse pan
            if world.is_clicking:
                world.angle[1] += -(get_mouse_x() - world.click_pos[0]) / 500
                world.angle[0] += (get_mouse_y() - world.click_pos[1]) / 500

                world.click_pos[0] = get_mouse_x()
                world.click_pos[1] = get_mouse_y()


def pan_start(world: World, x, y):
    world.click_pos = [x, y]
    world.is_clicking = True

def pan_end(world: World):
    world.is_clicking = False


def create_World() -> World:
    base = create_box([8,1,8], [0,1,0], "white")
    box1 = create_box([1, 1, 1], [0, 0, 2], "white")
    box2 = create_box([1,1,1], [0,0,0], "red")
    box3 = create_box([1,1,1], [-1, 0, -1], "blue")
    box4 = create_box([1,1,1], [2, 0, -1], "green")
    return World([[base],[box1],[box2],[box3],[box4]], [0.0, 0.0, 0.0], [0, 0], False)


when('starting', create_World)

when('input.mouse.down', pan_start)
when('input.mouse.up', pan_end)

when('updating', update_boxes)
start()