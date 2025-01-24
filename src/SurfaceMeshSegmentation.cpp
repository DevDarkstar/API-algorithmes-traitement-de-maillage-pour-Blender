#include "SurfaceMeshSegmentation.hpp"
#include <vector>
#include <chrono>
#include <iostream>
#include <boost/format.hpp>
#include <stdexcept>
#include <random>

namespace py = pybind11;
using namespace segmentation;

SurfaceMeshSegmentation::SurfaceMeshSegmentation(const py::dict& data) : m_surface_mesh(){
    //Toutes les données, provenant de notre structure de données python, sont castées vers leurs types C++ idoines
    const std::vector<double> vertices = data["vertices"].cast<std::vector<double>>();
    const std::vector<int> faces = data["faces"].cast<std::vector<int>>();
    py::list params = data["params"].cast<py::list>();
    py::dict algorithm_parameters = params[0].cast<py::dict>();
    this->m_clusters = algorithm_parameters["clusters"].cast<int>();
    this->m_smoothness = algorithm_parameters["smoothness"].cast<double>();
    this->m_output_option = data["options"]["output_option"].cast<std::string>();

    // Stockage du nombre de faces du maillage envoyé par Blender
    this->m_number_of_faces = faces.size() / 3;

    //création d"un tableau de vector_descriptor qui va contenir les informations des coordonnées des sommets du maillage
    std::vector<vertex_descriptor> vertices_descriptor;
    //et réservation de l"espace mémoire adéquat
    vertices_descriptor.reserve(vertices.size() / 3);

    for(int i = 0; i < vertices.size(); i+=3){
        vertices_descriptor.push_back(this->m_surface_mesh.add_vertex(Point_3(vertices[i], vertices[i+1], vertices[i+2])));       
    }

    for(int i = 0; i < faces.size(); i+=3){
        //Création d"une face du maillage
        this->m_surface_mesh.add_face(vertices_descriptor[faces[i]], vertices_descriptor[faces[i+1]], vertices_descriptor[faces[i+2]]);
    }

    std::cout << "Nombre de faces du maillage original " << this->m_surface_mesh.number_of_faces() << std::endl;
}

void SurfaceMeshSegmentation::compute_algorithm(){

    /*if(!CGAL::is_triangle_mesh(this->m_surface_mesh))
    {
        throw std::runtime_error("Le maillage n"est pas composé que de faces triangulaires...");
    }*/
    try{
        std::chrono::steady_clock::time_point start_time = std::chrono::steady_clock::now();
        Facet_double_map sdf_property_map;
        sdf_property_map = this->m_surface_mesh.add_property_map<face_descriptor, double>("f:sdf").first;

        // compute SDF values
        // We can"t use default parameters for number of rays, and cone angle
        // and the postprocessing
        CGAL::sdf_values(this->m_surface_mesh, sdf_property_map, 2.0 / 3.0 * CGAL_PI, 25, true);

        // create a property-map for segment-ids
        Facet_int_map segment_property_map = this->m_surface_mesh.add_property_map<face_descriptor,std::size_t>("f:sid").first;

        // segment the mesh using default parameters for number of levels, and smoothing lambda
        // Any other scalar values can be used instead of using SDF values computed using the CGAL function
        std::size_t number_of_segments = CGAL::segmentation_from_sdf_values(this->m_surface_mesh, sdf_property_map, segment_property_map, this->m_clusters, this->m_smoothness);
        std::chrono::steady_clock::time_point end_time = std::chrono::steady_clock::now();
        std::cout << "Number of segments: " << number_of_segments << std::endl;
        std::cout << "Time elapsed: " << std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count() << "ms" << std::endl;
 
        if(this->m_output_option == "SEGMENTS_COLOR"){
            //this->m_output_data["colors_number"] = number_of_segments; 
            this->set_segments_ids_to_colors(number_of_segments);
        }
        else{
            // Création du message de résultat
            boost::format message = boost::format("Paramètres utilisés :\n"
                                                "- nombre de clusters : %1%\n"
                                                "- finesse : %2%\n\n"
                                                "Nombre de segments obtenus : %3%.") 
                                    % this->m_clusters 
                                    % this->m_smoothness 
                                    % number_of_segments;
            this->m_output_data["result_infos"] = message.str();
            this->m_output_data["output_result"] = std::array<std::string,1>{"message"};
        }
    }catch(const std::exception& e){
        std::cerr << "Une erreur s'est produite lors de l'exécution de l'algorithme de segmentation de CGAL : " << e.what() << std::endl;
        throw;
    }
}

void SurfaceMeshSegmentation::set_segments_ids_to_colors(const size_t color_number){
    // Création d'un tableau contenant les opérations à exécuter sur l'algorithme une fois l'algorithme effectué
    std::vector<std::string> output_result;
    // Vérification si le nombre de faces reçu par Blender correspond bien au nombre de faces du maillage sur lequel l'algorithme a été effectué
    if (this->m_number_of_faces != this->m_surface_mesh.number_of_faces())
    {
        // Demande de recréer le maillage dans Blender
        output_result.push_back("replace_mesh");
        // et stockage des coordonnées des sommets ainsi que des indices des sommets des faces dans le dictionnaire des données exportées
        // Récupération de la propriété contenant les coordonnées des sommets du maillage
        const auto& location = this->m_surface_mesh.property_map<vertex_descriptor, Point_3>("v:point").first;

        std::vector<double> vertex_coordinates;
        vertex_coordinates.reserve(this->m_surface_mesh.number_of_vertices() * 3);

        for(const auto& vertex : this->m_surface_mesh.vertices()) {
            // Récupération des coordonnées du sommet courant
            const auto& coords = location[vertex];
            vertex_coordinates.push_back(coords.x());
            vertex_coordinates.push_back(coords.y());
            vertex_coordinates.push_back(coords.z());
        }

        this->m_output_data["vertices"] = vertex_coordinates;

        // et de même pour les faces
        std::vector<int> face_indices;
        face_indices.reserve(this->m_surface_mesh.number_of_faces() * 3);
        for(const auto& face: this->m_surface_mesh.faces()){
            for(const auto& vertex: vertices_around_face(this->m_surface_mesh.halfedge(face), this->m_surface_mesh)){
                face_indices.push_back(vertex.idx());
            }
        }

        this->m_output_data["faces"] = face_indices;
    }
    //Récupération de la property_map contenant les identifiants des segments obtenus
    const auto& segment_property_map = this->m_surface_mesh.property_map<face_descriptor, std::size_t>("f:sid").first;
    output_result.push_back("face_coloration");
    // Création des couleurs de façon aléatoire et permettant de remplir le tableau des couleurs des faces du maillage ultérieurement
    std::vector<std::array<float, 4>> colors;
    colors.reserve(color_number);

    std::cout << "Nombre de faces du maillage résultant " << this->m_surface_mesh.number_of_faces() << std::endl;

    // Génération aléatoire des couleurs
    // Initialisation de la génération de nombres psudo-aléatoires
    std::random_device rd;
    // Création du moteur de génération
    std::default_random_engine engine(rd());
    // Création de la méthode de génération des nombres entre 0 et 1 (ici une distribution uniforme)
    std::uniform_real_distribution<float> distribution(0, 1);

    // Génération des couleurs
    for (int i = 0; i < color_number; i++){
        // Ajout de la nouvelle couleur avec l'alpha dans le tableau des couleurs
        colors.emplace_back(std::array<float, 4>{distribution(engine), distribution(engine), distribution(engine), 1.0f});
    }
    // Création d'un tableau pour stocker les couleurs associées aux faces du maillage et réservation de l'espace mémoire
    std::vector<float> face_colors;
    face_colors.reserve(num_faces(this->m_surface_mesh) * 4);

    // Remplissage du tableau des couleurs des faces à partir des couleurs générées précédemment
    for(const auto& fd : faces(this->m_surface_mesh)){
        auto color = colors[segment_property_map[fd]];
        face_colors.insert(face_colors.cend(), color.cbegin(), color.cend());
    }

    this->m_output_data["colors"] = face_colors;
    this->m_output_data["output_result"] = output_result;
}
