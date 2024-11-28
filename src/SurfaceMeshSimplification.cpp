#include "SurfaceMeshSimplification.hpp"
#include <vector>
#include <chrono>
#include <iostream>
//#include <stdexcept>
#include <algorithm>

namespace SMS = CGAL::Surface_mesh_simplification;
namespace py = pybind11;
using namespace simplification;

SurfaceMeshSimplification::SurfaceMeshSimplification(const py::dict& data) : m_surface_mesh()
{
    //On caste toutes les données provenant de notre structure de données python vers des types C++
    const std::vector<int>& faces = data["faces"].cast<std::vector<int>>();
    const std::vector<double>& vertices = data["vertices"].cast<std::vector<double>>();
    this->m_stop_ratio = data["decimation_factor"].cast<double>();

    //création d"un tableau de vector_descriptor qui va contenir les informations des coordonnées des sommets du maillage
    std::vector<vertex_descriptor> vertices_descriptor;
    //et réservation de l"espace mémoire adéquat
    vertices_descriptor.reserve(vertices.size() / 3);

    for(int i = 0; i < vertices.size(); i+=3){
        vertices_descriptor.push_back(this->m_surface_mesh.add_vertex(Point_3(vertices[i], vertices[i+1], vertices[i+2])));
    }

    for(int i = 0; i < faces.size(); i+=3){
        //Création de la face du maillage
        this->m_surface_mesh.add_face(vertices_descriptor[faces[i]], vertices_descriptor[faces[i+1]], vertices_descriptor[faces[i+2]]);
    }
}

void SurfaceMeshSimplification::compute_algorithm()
{
    /*
    if(!CGAL::is_triangle_mesh(this->m_surface_mesh))
    {
        throw std::runtime_error("Le maillage n"est pas composé que de faces triangulaires...");
    }*/

    std::chrono::steady_clock::time_point start_time = std::chrono::steady_clock::now();
    // In this example, the simplification stops when the number of undirected edges
    // drops below 10% of the initial count
    SMS::Edge_count_ratio_stop_predicate<Surface_mesh> stop(this->m_stop_ratio);
    int r = SMS::edge_collapse(this->m_surface_mesh, stop);
    std::chrono::steady_clock::time_point end_time = std::chrono::steady_clock::now();
    std::cout << "\nFinished!\n" << r << " edges removed.\n" << this->m_surface_mesh.number_of_edges() << " final edges.\n";
    std::cout << "Time elapsed: " << std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count() << "ms" << std::endl;

    // Mise à jour des indices des sommets restants dans le maillage de sorte à ce que le premier sommet du maillage restant ait bien l"indice 0, le second l"indice 1, ...
    std::map<vertex_descriptor, int> vertex_reindexing = this->get_vertex_reindexing();

    this->update_vertex_coordinates(); 
    this->update_face_indices(vertex_reindexing);
    this->m_output_data["output_result"] = "new_mesh";
}

void SurfaceMeshSimplification::update_vertex_coordinates()
{
    //Création d"un tableau qui va contenir les coordonnées de nos nouveaux résultant de l"algorithme de simplification
    std::vector<double> vertices_coordinates;
    // réservation de l"espace mémoire adéquat
    vertices_coordinates.reserve(num_vertices(this->m_surface_mesh) * 3);

    //utilisation de propriétés : "location" référence les positions
    const auto& location = this->m_surface_mesh.property_map<vertex_descriptor, Point_3>("v:point").first;

    for(const auto& vertex : this->m_surface_mesh.vertices()) {
        // Récupération des coordonnées du sommet courant
        const auto& coords = location[vertex];
        vertices_coordinates.push_back(coords.x());
        vertices_coordinates.push_back(coords.y());
        vertices_coordinates.push_back(coords.z());
        //std::array<double,3> vertex{coords.x(), coords.y(), coords.z()};
        //vertices_coordinates.insert(vertices_coordinates.end(), vertex.cbegin(), vertex.cend());
    }

    //Ajout du tableau dans la structure de données qui sera retournée à Blender
    this->m_output_data["vertices"] = vertices_coordinates;
}

void SurfaceMeshSimplification::update_face_indices(std::map<vertex_descriptor, int>& vertex_reindexing)
{
    //Création d"un tableau qui va contenir les indices des sommets des faces résultant de l"algorithme de simplification
    std::vector<int> face_indices;
    // et réservation de l"espace mémoire adéquat
    face_indices.reserve(num_faces(this->m_surface_mesh) * 3);

    // Parcours des faces du maillage
    for(const auto& face : this->m_surface_mesh.faces()) {
        // Parcours des sommets appartenant à la face courante
        for(const auto& vertex : vertices_around_face(this->m_surface_mesh.halfedge(face), this->m_surface_mesh)) {
            // ajout du nouvel indice (obtenu par ré-indexation) du sommet dans le conteneur des indices de face
            face_indices.push_back(vertex_reindexing[vertex]);
        }
    }
    //Ajout du tableau dans la structure de données qui sera retournée à Blender
    this->m_output_data["faces"] = face_indices;
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