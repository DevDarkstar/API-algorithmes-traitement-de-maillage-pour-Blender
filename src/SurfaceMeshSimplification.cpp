#include "SurfaceMeshSimplification.hpp"
#include <pybind11/numpy.h>
#include <vector>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <algorithm>

namespace SMS = CGAL::Surface_mesh_simplification;
namespace py = pybind11;
using namespace simplification;

SurfaceMeshSimplification::SurfaceMeshSimplification(const py::dict& data) : m_surface_mesh()
{
    //On caste toutes les données provenant de notre structure de données python vers des types C++
    py::array_t<int> faces = data["faces"].cast<py::array_t<int>>();
    py::array_t<double> vertices = data["vertices"].cast<py::array_t<double>>();
    py::list params = data["params"].cast<py::list>();
    py::dict algorithm_parameters = params[0].cast<py::dict>();
    this->m_stop_ratio = py::float_(algorithm_parameters["decimation_factor"]);

    // Récupération des tailles des conteneurs des coordonnées des sommets et des indices des sommets des faces
    size_t vertices_size = static_cast<size_t>(vertices.shape(0));
    size_t faces_size = static_cast<size_t>(faces.shape(0));

    // Ainsi qu'un pointeur sur leurs données
    auto vertices_ptr = vertices.data();
    auto faces_ptr = faces.data();

    //création d"un tableau de vector_descriptor qui va contenir les informations des coordonnées des sommets du maillage
    std::vector<vertex_descriptor> vertices_descriptor;
    //et réservation de l"espace mémoire adéquat
    vertices_descriptor.reserve(vertices_size / 3);

    for(int i = 0; i < vertices_size; i+=3){
        vertices_descriptor.push_back(this->m_surface_mesh.add_vertex(Point_3(vertices_ptr[i], vertices_ptr[i+1], vertices_ptr[i+2])));
    }

    for(int i = 0; i < faces_size; i+=3){
        //Création de la face du maillage
        this->m_surface_mesh.add_face(vertices_descriptor[faces_ptr[i]], vertices_descriptor[faces_ptr[i+1]], vertices_descriptor[faces_ptr[i+2]]);
    }
}

void SurfaceMeshSimplification::compute_algorithm()
{
    /*
    if(!CGAL::is_triangle_mesh(this->m_surface_mesh))
    {
        throw std::runtime_error("Le maillage n"est pas composé que de faces triangulaires...");
    }*/
    try{
        std::chrono::steady_clock::time_point start_time = std::chrono::steady_clock::now();
        // In this example, the simplification stops when the number of undirected edges
        // drops below 10% of the initial count
        SMS::Edge_count_ratio_stop_predicate<Surface_mesh> stop(this->m_stop_ratio);
        int r = SMS::edge_collapse(this->m_surface_mesh, stop);
        std::chrono::steady_clock::time_point end_time = std::chrono::steady_clock::now();
        std::cout << "\nFinished!\n" << r << " edges removed.\n" << this->m_surface_mesh.number_of_edges() << " final edges.\n";
        std::cout << "Time elapsed: " << std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count() << "ms" << std::endl;
    }catch(const std::exception& e){
        std::cerr << "Une erreur s'est produite lors de l'éxécution de l'algorithme de décimation de CGAL : " << e.what() << std::endl;
        throw;
    }

    // Mise à jour des indices des sommets restants dans le maillage de sorte à ce que le premier sommet du maillage restant ait bien l"indice 0, le second l"indice 1, ...
    std::map<vertex_descriptor, int> vertex_reindexing = this->get_vertex_reindexing();

    this->update_vertex_coordinates(); 
    this->update_face_indices(vertex_reindexing);
    this->m_output_data["output_result"] = std::array<std::string,1>{"replace_mesh"};
}

void SurfaceMeshSimplification::update_vertex_coordinates()
{
    //Création d'un tableau qui va contenir les coordonnées de nos nouveaux résultant de l'algorithme de décimation
    py::array_t<double> vertices_coordinates({static_cast<py::ssize_t>(this->m_surface_mesh.vertices().size() * 3)});
    // Récupération d'un pointeur sur le conteneur des données
    auto vertices_coordinates_ptr = vertices_coordinates.mutable_data();
    // Création d'un compteur sur le nombre de données stockées
    size_t v = 0;

    //utilisation de propriétés : "location" référence les positions
    const auto& location = this->m_surface_mesh.property_map<vertex_descriptor, Point_3>("v:point").first;

    for(const auto& vertex : this->m_surface_mesh.vertices()) {
        // Récupération des coordonnées du sommet courant
        const auto& coords = location[vertex];
        vertices_coordinates_ptr[v] = coords.x();
        vertices_coordinates_ptr[v+1] = coords.y();
        vertices_coordinates_ptr[v+2] = coords.z();
        // Mise à jour du compteur
        v += 3;
    }

    //Ajout du tableau dans la structure de données qui sera retournée à Blender
    this->m_output_data["vertices"] = std::move(vertices_coordinates);
}

void SurfaceMeshSimplification::update_face_indices(std::map<vertex_descriptor, int>& vertex_reindexing)
{
    //Création d'un tableau qui va contenir les indices des sommets des faces résultant de l'algorithme de décimation
    py::array_t<int> face_indices({static_cast<py::ssize_t>(this->m_surface_mesh.faces().size() * 3)});
    // Récupération d'un pointeur sur le conteneur des données
    auto face_indices_ptr = face_indices.mutable_data();
    // Création d'un compteur sur le nombre de données stockées
    size_t f = 0;

    // Parcours des faces du maillage
    for(const auto& face : this->m_surface_mesh.faces()) {
        // Parcours des sommets appartenant à la face courante
        for(const auto& vertex : vertices_around_face(this->m_surface_mesh.halfedge(face), this->m_surface_mesh)) {
            // ajout du nouvel indice (obtenu par ré-indexation) du sommet dans le conteneur des indices de face
            face_indices_ptr[f] = vertex_reindexing[vertex];
            // Incrémentation du compteur
            f++;
        }
    }
    //Ajout du tableau dans la structure de données qui sera retournée à Blender
    this->m_output_data["faces"] = std::move(face_indices);
}

std::map<vertex_descriptor, int> SurfaceMeshSimplification::get_vertex_reindexing()
{   
    std::map<vertex_descriptor, int> vertex_reindexing;
    // Pour ré-indexer le maillage, nous allons parcourir l"ensemble des sommets du maillage
    // et associer pour chacun d"entre eux un indice qui ira de 0 au nombre de sommets du maillage - 1
    int new_index = 0;
    for (const auto& vertex : this->m_surface_mesh.vertices()) {
        vertex_reindexing[vertex] = new_index++;
    }

    return vertex_reindexing;
}
