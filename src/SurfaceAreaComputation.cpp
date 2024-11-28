#include "SurfaceAreaComputation.hpp"
#include <boost/format.hpp>

namespace py = pybind11;
using namespace cgal_area_computation;

SurfaceAreaComputation::SurfaceAreaComputation(const py::dict& data) : m_vertex_coordinates()
{
    //On caste toutes les données provenant de notre structure de données python vers des types C++
    const std::vector<int> faces = data["faces"].cast<std::vector<int>>();
    const std::vector<double> vertices = data["vertices"].cast<std::vector<double>>();

    // Récupération des tailles des deux conteneurs
    const size_t vertex_number = vertices.size();
    const size_t face_number = faces.size();

    //création d"un tableau de vector_descriptor qui va contenir les informations des coordonnées des sommets du maillage
    std::vector<Point_3> vertex_coordinates;
    //et réservation de l"espace mémoire adéquat
    vertex_coordinates.reserve(vertex_number / 3);

    // Création et stockage des points du maillage sous la forme de Point_3
    for(int i = 0; i < vertex_number; i+=3){
        vertex_coordinates.emplace_back(Point_3(vertices[i], vertices[i+1], vertices[i+2]));
    }

    // Et création du tableau des faces ou chaque itération correspond aux coordonnées des sommets formant la face
    // Réservation de l"espace mémoire requis
    this->m_vertex_coordinates.reserve(face_number / 3);
    // et remplissage du conteneur
    for(int i = 0; i < face_number; i+=3){
        //std::array<Point_3, 3> face = {vertex_coordinates[faces[i]], vertex_coordinates[faces[i+1]], vertex_coordinates[faces[i+2]]};
        this->m_vertex_coordinates.emplace_back(std::array<Point_3,3>{vertex_coordinates[faces[i]], vertex_coordinates[faces[i+1]], vertex_coordinates[faces[i+2]]});
    }
}

void SurfaceAreaComputation::compute_algorithm(){
    // Initialisation d"une variable contenant l"aire totale du maillage
    double area = 0.0;

    // Parcours des faces du maillage
    for(const auto& face: this->m_vertex_coordinates){
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
    this->m_output_data["output_result"] = "message";
}