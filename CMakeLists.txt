# Created by the script cgal_create_CMakeLists
# This is the CMake script for compiling a set of CGAL applications.

cmake_minimum_required(VERSION 3.20)

project( cgal_api LANGUAGES CXX)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -flto=auto")
file(GLOB SOURCES "src/*.cpp")

# Inclure Pybind11
if(WIN32)
	set(PYBIND11_FINDPYTHON ON)
endif()
add_subdirectory(libraries/pybind11)

# Création du module Pybind11 en incluant tous les fichiers .cpp
pybind11_add_module(algorithms_api ${SOURCES})

# Rechercher CGAL
find_package(CGAL QUIET COMPONENTS)

# Inclure les fichiers de CGAL
include(${CGAL_USE_FILE})
include_directories(${Boost_INCLUDE_DIRS})

if(UNIX)
	target_link_libraries(algorithms_api PRIVATE CGAL::CGAL)
endif()
