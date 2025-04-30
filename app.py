from flask import Flask, request, jsonify, render_template
import networkx as nx
import random
import numpy as np
import logging
from functools import lru_cache


app = Flask(__name__)

# Cache global pour stocker les résultats d'optimisation déjà calculés (clé = (start, end))
route_cache = {}

# ---------------------------
# Définition du Graphe de la Chaîne d'Approvisionnement au Maroc
# ---------------------------
G = nx.Graph()

# Définition des emplacements principaux (warehouses) avec leurs coordonnées (latitude, longitude)
locations = {
    "Tangier": (35.7595, -5.83395),
    "Tetouan": (35.5780, -5.3690),
    "Rabat": (34.020882, -6.841650),
    "Kenitra": (34.2580, -6.5700),
    "Casablanca": (33.5731, -7.5898),
    "Marrakech": (31.6295, -7.9811),
    "Agadir": (30.4278, -9.5981)
}

# Ajout des nœuds principaux au graphe
for location, coords in locations.items():
    G.add_node(location, pos=coords)

# Définition des routes directes entre villes principales avec une distance approximative (en km)
routes = [
    ("Tangier", "Tetouan", 60),
    ("Tangier", "Rabat", 250),
    ("Tetouan", "Rabat", 200),
    ("Rabat", "Kenitra", 70),
    ("Rabat", "Casablanca", 90),
    ("Kenitra", "Casablanca", 150),
    ("Casablanca", "Marrakech", 210),
    ("Marrakech", "Agadir", 240)
]
G.add_weighted_edges_from(routes)

# ---------------------------
# Définition des intersections et villes supplémentaires
# ---------------------------
# Fusionne toutes les intersections et ajoute des villes majeures supplémentaires
intersections = {
    "Intersection1": (32.6000, -7.7850),   # Entre Casablanca et Marrakech
    "Intersection2": (31.0300, -8.7900),     # Entre Marrakech et Agadir
    "Larache": (35.1700, -6.1700),           # Ville du nord
    "Assilah": (35.7400, -6.0600),            # Ville côtière du nord-ouest
    "Meknes": (33.8900, -5.5500),             # Ville au nord-centre
    "El Jadida": (33.2470, -8.5000),          # Ville côtière près de Casablanca
    "Fez": (34.0333, -5.0000),               # Grande ville historique
    "Oujda": (34.6800, -1.9000),             # Ville de l'est, proche de la frontière algérienne
    "Ouarzazate": (30.9333, -6.9333),         # Porte du Sahara
    "Essaouira": (31.5085, -9.7631),          # Ville côtière près de Marrakech
    "Safi": (32.2994, -9.2316),              # Ville industrielle côtière
    "Beni Mellal": (32.3384, -6.3600),         # Ville du plateau central
    # Ajouts supplémentaires pour une meilleure couverture du territoire
    "Nador": (35.1681, -3.0167),             # Nord-est
    "Mohammedia": (33.6870, -7.4241),        # Près de Casablanca
    "Khemisset": (33.8450, -6.2110),         # Proche de Rabat
    "Settat": (33.0056, -7.6164),            # Sud-ouest de Rabat
    "Taza": (34.2100, -3.0000),              # Intérieur du nord-est
    "Chefchaouen": (35.1710, -5.2697),       # Ville bleue dans le Rif
    "Midelt": (32.7440, -4.7130),            # Région du Moyen Atlas
    "Al Hoceima": (35.2580, -3.9370),        # Côte méditerranéenne nord
    "Tiznit": (29.7000, -8.8000)             # Ville du sud près d'Agadir
}

# Ajout de tous les nœuds d'intersections au graphe
for node, coords in intersections.items():
    G.add_node(node, pos=coords)

# ---------------------------
# Définition des arêtes supplémentaires pour améliorer la connectivité du réseau
# ---------------------------
extra_edges = [
    # Connexions dans le nord
    ("Tangier", "Assilah", 40),
    ("Tangier", "Larache", 50),
    ("Assilah", "Larache", 20),
    ("Tetouan", "Fez", 150),
    ("Fez", "Meknes", 50),
    ("Meknes", "Rabat", 70),
    ("Kenitra", "Meknes", 50),
    # Permet d'obtenir un chemin direct de Larache à Kenitra
    ("Larache", "Kenitra", 110),
    # Permet d'accéder à Larache depuis Tetouan pour ensuite aller vers Kenitra
    ("Tetouan", "Larache", 70),
    # Liens le long de la côte
    ("Casablanca", "El Jadida", 60),
    ("Casablanca", "Safi", 100),
    ("Safi", "El Jadida", 50),
    # Renforcer la connexion Casablanca-Marrakech via une intersection
    ("Casablanca", "Intersection1", 105),
    ("Intersection1", "Marrakech", 105),
    # Connexion entre Marrakech et Agadir via une intersection
    ("Marrakech", "Intersection2", 120),
    ("Intersection2", "Agadir", 120),
    # Liens supplémentaires dans le sud et l'est
    ("Marrakech", "Essaouira", 190),
    ("Essaouira", "Agadir", 170),
    ("Fez", "Oujda", 250),
    ("Oujda", "Rabat", 400),
    ("Beni Mellal", "Meknes", 90),
    ("Beni Mellal", "Casablanca", 150),
    # Connecter Ouarzazate comme point stratégique dans le sud
    ("Marrakech", "Ouarzazate", 190),
    ("Ouarzazate", "Agadir", 220),
    # Nouveaux liens pour améliorer la connectivité
    ("Mohammedia", "Casablanca", 20),
    ("Mohammedia", "Rabat", 30),
    ("Nador", "Oujda", 80),
    ("Chefchaouen", "Tangier", 60),
    ("Chefchaouen", "Tetouan", 40),
    ("Taza", "Fez", 60),
    ("Khemisset", "Rabat", 50),
    ("Settat", "Casablanca", 70),
    ("Midelt", "Meknes", 70),
    ("Al Hoceima", "Oujda", 100),
    ("Tiznit", "Agadir", 50)
]
# Ajoute toutes les arêtes supplémentaires au graphe
G.add_weighted_edges_from(extra_edges)

# ---------------------------
# Implémentation de l'Algorithme de Colonie d'Abeilles (ABC)
# ---------------------------
class ArtificialBeeColony:
    """
    Implémente l'algorithme de colonie d'abeilles pour l'optimisation d'une chaîne d'approvisionnement.
    """
    def __init__(self, G, start, end, num_bees=20, max_iterations=100, eps=0.001):
        self.G = G
        self.start = start
        self.end = end
        self.num_bees = num_bees
        self.max_iterations = max_iterations
        self.eps = eps  # Petite valeur pour éviter la division par zéro
        
        # Liste pour stocker les logs de chaque itération
        self.iteration_logs = []
        # Compteur global pour détecter une stagnation prolongée
        self.patience_total = 0

        # Générer la population initiale avec une limite de profondeur (cutoff) pour éviter l'explosion combinatoire
        self.current_population = [self.generate_possible_solution() for _ in range(self.num_bees)]
        # Filtrer les solutions non valides (None)
        self.current_population = [sol for sol in self.current_population if sol is not None]
        if not self.current_population:
            raise ValueError("Aucune solution candidate initiale trouvée.")
        
        # Trier la population selon la fitness (meilleure solution en première position)
        self.current_population = self.sort_population_by_fitness(self.current_population)
        self.current_best_solution = self.current_population[0]
        
        # Définition du nombre d'abeilles employées et observatrices
        self.num_employeed_bees = len(self.current_population) // 2
        self.num_onlooker_bees = len(self.current_population) - self.num_employeed_bees

    def evaluate_fitness(self, path):
        """
        Calcule la fitness d'un chemin comme l'inverse de son coût total.
        Plus le coût est faible, meilleure est la fitness.
        """
        total_cost = 0.0
        for i in range(1, len(path)):
            # Si une arête existe, ajouter sa distance, sinon ajouter un coût très élevé
            if self.G.has_edge(path[i-1], path[i]):
                total_cost += self.G[path[i-1]][path[i]]['weight']
            else:
                total_cost += 1e6
        return 1.0 / (total_cost + self.eps)

    def total_cost(self, path):
        """Calcule et retourne le coût total d'un chemin."""
        cost = 0.0
        for i in range(1, len(path)):
            if self.G.has_edge(path[i-1], path[i]):
                cost += self.G[path[i-1]][path[i]]['weight']
            else:
                cost += 1e6
        return cost

    def generate_possible_solution(self):
        """
        Génère une solution candidate :
          - Utilise nx.all_simple_paths avec un cutoff pour limiter la profondeur.
          - Applique une heuristique d'insertion pour ajouter un nœud intermédiaire pertinent.
        """
        try:
            all_paths = list(nx.all_simple_paths(self.G, source=self.start, target=self.end, cutoff=10))
        except nx.NetworkXNoPath:
            return None
        if not all_paths:
            return None
        # Choix aléatoire d'un chemin parmi ceux trouvés
        candidate = random.choice(all_paths)
        
        # Avec une probabilité de 30%, tente d'améliorer le chemin en insérant un nœud supplémentaire
        if random.random() < 0.3:
            # Sélectionner les nœuds non présents dans le chemin actuel
            possible_nodes = [node for node in self.G.nodes() if node not in candidate]
            if possible_nodes:
                # Échantillonner jusqu'à 5 candidats pour l'insertion
                sample = random.sample(possible_nodes, min(5, len(possible_nodes)))
                best_node = None
                best_insertion = None
                best_extra_cost = float('inf')
                # Pour chaque nœud candidat, tester chaque position d'insertion possible
                for node in sample:
                    for i in range(1, len(candidate)):
                        # Coût de la connexion actuelle entre candidate[i-1] et candidate[i]
                        cost_without = self.G[candidate[i-1]][candidate[i]]['weight'] if self.G.has_edge(candidate[i-1], candidate[i]) else 1e6
                        # Coût si le nœud était inséré entre candidate[i-1] et candidate[i]
                        if self.G.has_edge(candidate[i-1], node) and self.G.has_edge(node, candidate[i]):
                            cost_with = self.G[candidate[i-1]][node]['weight'] + self.G[node][candidate[i]]['weight']
                        else:
                            cost_with = 1e6
                        extra_cost = cost_with - cost_without
                        # Sélectionne l'insertion qui augmente le moins le coût
                        if extra_cost < best_extra_cost:
                            best_extra_cost = extra_cost
                            best_node = node
                            best_insertion = i
                if best_node is not None:
                    candidate = candidate[:best_insertion] + [best_node] + candidate[best_insertion:]
        return candidate

    def generate_random_subpath(self, from_node, to_node, max_attempts=50):
        """
        Génère un sous-chemin aléatoire entre deux nœuds en évitant les cycles.
        Tente jusqu'à max_attempts pour trouver un chemin valide.
        """
        path = [from_node]
        current = from_node
        attempts = 0
        while current != to_node and attempts < max_attempts:
            neighbors = list(self.G.neighbors(current))
            # Évite de revisiter les nœuds déjà dans le chemin, sauf si c'est le nœud de destination
            valid_neighbors = [n for n in neighbors if n not in path or n == to_node]
            if not valid_neighbors:
                return None
            next_node = random.choice(valid_neighbors)
            path.append(next_node)
            current = next_node
            attempts += 1
        return path if current == to_node else None

    def apply_random_neighborhood_structure(self, path):
        """
        Applique une modification locale sur le chemin pour tenter de l'améliorer.
        Une sous-partie du chemin est remplacée par un nouveau sous-chemin généré aléatoirement.
        """
        if len(path) < 3:
            return path
        # Choisit un indice aléatoire à l'intérieur du chemin (hors extrémités)
        i = random.randint(1, len(path) - 2)
        new_segment = self.generate_random_subpath(path[i-1], path[i+1])
        if new_segment is None or len(new_segment) < 2:
            return path
        # Construit un nouveau chemin en insérant le nouveau segment
        new_path = path[:i] + new_segment[1:] + path[i+1:]
        # Supprime les doublons tout en conservant l'ordre des nœuds
        seen = set()
        filtered_path = []
        for node in new_path:
            if node not in seen:
                filtered_path.append(node)
                seen.add(node)
        # Vérifie que le chemin commence et se termine par les nœuds attendus
        if filtered_path[0] != self.start or filtered_path[-1] != self.end:
            return path
        return filtered_path

    def choose_solution_with_probability(self, population, probability_list):
        """
        Sélectionne une solution dans la population en fonction de la distribution de probabilité dérivée de la fitness.
        """
        r = random.random()
        cumulative_probability = 0.0
        for i, sol in enumerate(population):
            cumulative_probability += probability_list[i]
            if r <= cumulative_probability:
                return sol
        return population[-1]

    def sort_population_by_fitness(self, population):
        """Trie la population par fitness décroissante (meilleure solution en première position)."""
        return sorted(population, key=lambda x: self.evaluate_fitness(x), reverse=True)

    def run(self, patience=10):
        """
        Exécute l'algorithme ABC sur un nombre fixe d'itérations.
        Si la solution stagne, de nouvelles solutions sont ajoutées pour diversifier l'exploration.
        Retourne le meilleur chemin trouvé, son coût total et les logs d'itération.
        """
        best_fitness = self.evaluate_fitness(self.current_best_solution)
        patience_counter = 0

        for iteration in range(self.max_iterations):
            # Phase des abeilles employées : améliore les solutions existantes localement
            for i in range(self.num_employeed_bees):
                candidate = self.current_population[i]
                new_candidate = self.apply_random_neighborhood_structure(candidate)
                if new_candidate is None:
                    continue
                if self.evaluate_fitness(new_candidate) > self.evaluate_fitness(candidate):
                    self.current_population[i] = new_candidate

            # Phase des abeilles observatrices : sélection probabiliste et amélioration des solutions choisies
            fitness_values = [self.evaluate_fitness(sol) for sol in self.current_population]
            total_fitness = sum(fitness_values)
            probability_list = [f / total_fitness for f in fitness_values]
            for i in range(self.num_onlooker_bees):
                selected = self.choose_solution_with_probability(self.current_population, probability_list)
                new_candidate = self.apply_random_neighborhood_structure(selected)
                if new_candidate is None:
                    continue
                if self.evaluate_fitness(new_candidate) > self.evaluate_fitness(selected):
                    idx = self.current_population.index(selected)
                    self.current_population[idx] = new_candidate

            # Réorganisation de la population après modifications
            self.current_population = self.sort_population_by_fitness(self.current_population)
            current_best = self.current_population[0]
            current_best_fit = self.evaluate_fitness(current_best)
            
            # Mise à jour du meilleur chemin et réinitialisation du compteur de stagnation si amélioration
            if current_best_fit > best_fitness:
                self.current_best_solution = current_best
                best_fitness = current_best_fit
                patience_counter = 0
                self.patience_total = 0
            else:
                patience_counter += 1
                self.patience_total += 1

            # En cas de stagnation prolongée, ajouter de nouvelles solutions pour diversifier la population
            if self.patience_total >= patience * 3:
                new_sol = self.generate_possible_solution()
                if new_sol:
                    self.current_population.append(new_sol)
                    # Réorganisation et recalcul de la répartition des abeilles
                    self.current_population = self.sort_population_by_fitness(self.current_population)
                    self.num_employeed_bees = len(self.current_population) // 2
                    self.num_onlooker_bees = len(self.current_population) - self.num_employeed_bees
                self.patience_total = 0

            # Enregistrer les logs de cette itération
            cost = self.total_cost(self.current_best_solution)
            log_msg = f"Iteration {iteration+1}: Best Route={self.current_best_solution}, Cost={cost:.2f}, Fitness={best_fitness:.5f}"
            self.iteration_logs.append(log_msg)
            logging.info(log_msg)

            # Si aucune amélioration pendant 'patience' itérations, remplacer une solution par une nouvelle
            if patience_counter >= patience:
                new_sol = self.generate_possible_solution()
                if new_sol:
                    self.current_population[-1] = new_sol
                patience_counter = 0

        best_route = self.current_best_solution
        best_cost = self.total_cost(best_route)
        return best_route, best_cost, self.iteration_logs

# ---------------------------
# Définition des Routes Flask
# ---------------------------
@app.route('/')
def home():
    # Affiche la page d'accueil avec la carte et les options de sélection
    return render_template('index.html', locations=locations)

@app.route('/optimize', methods=['POST'])
def optimize():
    # Récupère les données JSON envoyées (start et end)
    data = request.json
    start = data.get('start')
    end = data.get('end')
    
    # Vérifie que les points de départ et d'arrivée sont valides
    if start not in locations or end not in locations or start == end:
        return jsonify({"error": "Invalid start or end location."}), 400

    # Utilise le cache pour retourner immédiatement un résultat déjà calculé
    cache_key = (start, end)
    if cache_key in route_cache:
        logging.info("Returning cached result for %s to %s", start, end)
        return jsonify(route_cache[cache_key])

    try:
        # Instancie l'algorithme ABC avec les paramètres spécifiés
        abc = ArtificialBeeColony(G, start, end, num_bees=20, max_iterations=100)
        best_route, best_cost, logs = abc.run(patience=10)
    except Exception as e:
        logging.error("Error during optimization: %s", e)
        return jsonify({"error": str(e)}), 500

    if best_route is None:
        return jsonify({"error": "No valid route found."}), 404

    # Récupère toutes les positions (coordonnées) des nœuds du graphe
    all_locations = {node: G.nodes[node]['pos'] for node in G.nodes}

    # Prépare le résultat à retourner sous forme de JSON
    result = {
        "route": best_route,
        "distance": best_cost,
        "abc_logs": logs,
        "all_locations": all_locations
    }
    # Stocke le résultat dans le cache
    route_cache[cache_key] = result
    return jsonify(result)

# ---------------------------


if __name__ == '__main__':
    app.run(debug=True)
