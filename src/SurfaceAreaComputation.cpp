#include "SurfaceAreaComputation.hpp"
#include <pybind11/numpy.h>
#include <boost/format.hpp>

namespace py = pybind11;
using namespace cgal_area_computation;

SurfaceAreaComputation::SurfaceAreaComputation(const py::dict& data) : m_faces()
{
    //On caste toutes les données provenant de notre structure de données python vers des types C++
    py::array_t<int> faces = data["faces"].cast<py::array_t<int>>();
    py::array_t<double> vertices = data["vertices"].cast<py::array_t<double>>();

    // Récupération des tailles des deux conteneurs
    const size_t vertices_size = static_cast<size_t>(vertices.shape(0));
    const size_t faces_size = static_cast<size_t>(faces.shape(0));

    // Récupération d'un pointeur sur les données des deux conteneurs
    auto vertices_ptr = vertices.data();
    auto faces_ptr = faces.data();

    //création d"un tableau de vector_descriptor qui va contenir les informations des coordonnées des sommets du maillage
    std::vector<Point_3> vertex_coordinates;
    //et réservation de l"espace mémoire adéquat
    vertex_coordinates.reserve(vertices_size / 3);

    // Création et stockage des points du maillage sous la forme de Point_3
    for(int i = 0; i < vertices_size; i+=3){
        vertex_coordinates.emplace_back(Point_3(vertices_ptr[i], vertices_ptr[i+1], vertices_ptr[i+2]));
    }

    // Et création du tableau des faces ou chaque itération correspond aux coordonnées des sommets formant la face
    // Réservation de l"espace mémoire requis
    this->m_faces.reserve(faces_size / 3);
    // et remplissage du conteneur
    for(int i = 0; i < faces_size; i+=3){
        //std::array<Point_3, 3> face = {vertex_coordinates[faces[i]], vertex_coordinates[faces[i+1]], vertex_coordinates[faces[i+2]]};
        this->m_faces.emplace_back(std::array<Point_3,3>{vertex_coordinates[faces_ptr[i]], vertex_coordinates[faces_ptr[i+1]], vertex_coordinates[faces_ptr[i+2]]});
    }
}

void SurfaceAreaComputation::compute_algorithm(){
    // Initialisation d"une variable contenant l"aire totale du maillage
    double area = 0.0;

    // Parcours des faces du maillage
    for(const auto& face: this->m_faces){
        // Création de deux vecteurs appartenant à la face courante
        Vector_3 vec1 = face[1] - face[0];
        Vector_3 vec2 = face[2] - face[0];

        // Calcul de l"aire de la face revenant à calculer la norme du produit vectoriel de vec1 et vec2 et de diviser le résultat par 2
        // et ajout du résultat dans l"aire totale du maillage
        area += CGAL::sqrt(CGAL::cross_product(vec1, vec2).squared_length()) / 2.0;
    }

    // Création du message de résultat
    boost::format message = boost::format("Aire du maillage : %1% m².") % area; 
    this->m_output_data["result_infos"] = message.str();
    this->m_output_data["output_result"] = std::array<std::string,1>{"message"};
}
