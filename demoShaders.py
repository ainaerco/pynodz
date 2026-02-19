"""Demo shader definitions for testing nodeAttrs.py without Arnold.

This module provides sample shader definitions that exercise all attribute
widget types in nodeAttrs.py, allowing demonstration of the node editor
without external dependencies.
"""


def getDemoShaders():
    """Return a dictionary of demo shader definitions.

    Each shader demonstrates different attribute types from nodeAttrs.py:
    - BOOL, FLOAT, INT, ENUM, RGB, RGBA, VECTOR, POINT, POINT2
    - STRING, MATRIX
    - Array types: FLOAT[], POINT[], INT[], VECTOR[], MATRIX[]
    - STRING[], RGB[] (ramp)
    """
    return {
        "DemoAllTypes": {
            "attributes": {
                "bool_attr": {
                    "name": "bool_attr",
                    "type": "BOOL",
                    "default": True,
                    "help": "Boolean toggle demonstration",
                },
                "float_attr": {
                    "name": "float_attr",
                    "type": "FLOAT",
                    "default": 0.5,
                    "softmin": 0.0,
                    "softmax": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "help": "Float slider with soft/hard limits",
                },
                "int_attr": {
                    "name": "int_attr",
                    "type": "INT",
                    "default": 10,
                    "min": 0,
                    "max": 100,
                    "help": "Integer input with range",
                },
                "enum_attr": {
                    "name": "enum_attr",
                    "type": "ENUM",
                    "default": "option1",
                    "enum": ["option1", "option2", "option3", "option4"],
                    "help": "Dropdown enumeration selection",
                },
                "rgb_attr": {
                    "name": "rgb_attr",
                    "type": "RGB",
                    "default": [1.0, 0.5, 0.0],
                    "help": "RGB color value",
                },
                "rgba_attr": {
                    "name": "rgba_attr",
                    "type": "RGBA",
                    "default": [1.0, 0.5, 0.0, 1.0],
                    "help": "RGBA color with alpha",
                },
                "vector_attr": {
                    "name": "vector_attr",
                    "type": "VECTOR",
                    "default": [0.0, 1.0, 0.0],
                    "help": "3D Vector value",
                },
                "point_attr": {
                    "name": "point_attr",
                    "type": "POINT",
                    "default": [0.0, 0.0, 0.0],
                    "help": "3D Point coordinates",
                },
                "point2_attr": {
                    "name": "point2_attr",
                    "type": "POINT2",
                    "default": [0.5, 0.5],
                    "help": "2D Point coordinates",
                },
                "string_attr": {
                    "name": "string_attr",
                    "type": "STRING",
                    "default": "hello world",
                    "help": "String text input",
                },
                "matrix_attr": {
                    "name": "matrix_attr",
                    "type": "MATRIX",
                    "default": "",
                    "help": "4x4 Matrix input",
                },
                "float_array": {
                    "name": "float_array",
                    "type": "FLOAT[]",
                    "default": [],
                    "help": "Array of float values (spline)",
                },
                "int_array": {
                    "name": "int_array",
                    "type": "INT[]",
                    "default": [],
                    "help": "Array of integer values",
                },
                "vector_array": {
                    "name": "vector_array",
                    "type": "VECTOR[]",
                    "default": [],
                    "help": "Array of vectors",
                },
                "string_array": {
                    "name": "string_array",
                    "type": "STRING[]",
                    "default": [],
                    "help": "Array of strings",
                },
                "ramp_attr": {
                    "name": "ramp_attr",
                    "type": "RGB[]",
                    "default": [],
                    "help": "Color ramp (RGB array)",
                },
            },
            "attributes_order": [
                "bool_attr",
                "float_attr",
                "int_attr",
                "enum_attr",
                "rgb_attr",
                "rgba_attr",
                "vector_attr",
                "point_attr",
                "point2_attr",
                "string_attr",
                "matrix_attr",
                "float_array",
                "int_array",
                "vector_array",
                "string_array",
                "ramp_attr",
            ],
            "help": "Demonstrates all attribute widget types",
        },
        "DemoMath": {
            "attributes": {
                "operation": {
                    "name": "operation",
                    "type": "ENUM",
                    "default": "add",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "help": "Mathematical operation",
                },
                "input_a": {
                    "name": "input_a",
                    "type": "FLOAT",
                    "default": 0.0,
                    "softmin": -10.0,
                    "softmax": 10.0,
                    "help": "First input value",
                },
                "input_b": {
                    "name": "input_b",
                    "type": "FLOAT",
                    "default": 1.0,
                    "softmin": -10.0,
                    "softmax": 10.0,
                    "help": "Second input value",
                },
                "result": {
                    "name": "result",
                    "type": "FLOAT",
                    "default": 0.0,
                    "help": "Result output",
                },
            },
            "attributes_order": ["operation", "input_a", "input_b", "result"],
            "help": "Simple math operation node",
        },
        "DemoColor": {
            "attributes": {
                "base_color": {
                    "name": "base_color",
                    "type": "RGB",
                    "default": [0.8, 0.2, 0.2],
                    "help": "Base diffuse color",
                },
                "roughness": {
                    "name": "roughness",
                    "type": "FLOAT",
                    "default": 0.5,
                    "softmin": 0.0,
                    "softmax": 1.0,
                    "help": "Surface roughness",
                },
                "metallic": {
                    "name": "metallic",
                    "type": "FLOAT",
                    "default": 0.0,
                    "softmin": 0.0,
                    "softmax": 1.0,
                    "help": "Metallic factor",
                },
                "emission": {
                    "name": "emission",
                    "type": "RGBA",
                    "default": [0.0, 0.0, 0.0, 1.0],
                    "help": "Emissive color",
                },
            },
            "attributes_order": [
                "base_color",
                "roughness",
                "metallic",
                "emission",
            ],
            "help": "Material color and properties",
        },
    }
