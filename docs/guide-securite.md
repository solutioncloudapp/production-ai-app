# Guide de Sécurité — Triple Couche de Défense

## Vue d'ensemble

La couche de sécurité implémente trois lignes de défense successives pour protéger l'application contre les injections de prompts, les données sensibles et les contenus inappropriés.

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layer                           │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Couche 1 : Input Guard                   │  │
│  │  • Détection d'injection de prompts (8 patterns)      │  │
│  │  • Détection de PII (SSN, CB, email)                  │  │
│  │  • Limite de longueur (4000 caractères)               │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Couche 2 : Content Filter                │  │
│  │  • Toxicité et langage haineux                        │  │
│  │  • Contenu sexuel                                     │  │
│  │  • Violence et auto-mutilation                        │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         ▼                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Couche 3 : Output Filter                 │  │
│  │  • Sanitisation Markdown                              │  │
│  │  • Suppression HTML/JS                                │  │
│  │  • Vérification des citations                         │  │
│  │  • Limite de longueur (4000 caractères)               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Input Guard — Première Ligne de Défense

**Fichier** : [`app/security/input_guard.py`](../app/security/input_guard.py)

Valide et sanitise toutes les entrées utilisateur avant qu'elles n'atteignent le LLM.

### Détection d'Injections de Prompts

8 patterns regex détectent les tentatives d'injection :

| Pattern | Exemple détecté |
|---------|-----------------|
| `ignore\s+(previous\|all)\s+(instructions\|rules\|prompts)` | "Ignore previous instructions" |
| `system\s*:\s*` | "System: You are now..." |
| `<\|.*?\|>` | Tags spéciaux de modèles |
| `\[INST\].*\[/INST\]` | Format d'instruction Mistral |
| `###\s*Instruction` | Format Alpaca |
| `act\s+as\s+(system\|admin\|developer)` | "Act as system admin" |
| `forget\s+(all\|your)\s+(instructions\|rules)` | "Forget all your rules" |
| `you\s+are\s+now\s+(in\s+)?(developer\|system)\s+mode` | "You are now in developer mode" |

### Détection et Redaction de PII

3 types de données sensibles sont détectés et remplacés par `[REDACTED_<type>]` :

| Type | Pattern | Exemple |
|------|---------|---------|
| SSN | `\b\d{3}[-.]?\d{2}[-.]?\d{4}\b` | `123-45-6789` → `[REDACTED_SSN]` |
| Carte bancaire | `\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b` | `4111-1111-1111-1111` → `[REDACTED_Credit Card]` |
| Email | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b` | `user@example.com` → `[REDACTED_Email]` |

### Vérifications supplémentaires

- **Limite de longueur** : 4000 caractères maximum (configurable via `MAX_INPUT_LENGTH`)
- **Input vide** : Rejeté avec message d'erreur
- **Sanitisation de base** : Suppression des caractères de contrôle et normalisation des espaces

### Flux de validation

```
Requête brute
    │
    ▼
Vérification longueur ──► > 4000 chars ──► BLOCKED
    │
    ▼
Vérification vide ──► Vide ──► BLOCKED
    │
    ▼
Vérification injections ──► Pattern détecté ──► BLOCKED
    │
    ▼
Détection PII ──► PII trouvée ──► Redaction
    │
    ▼
Requête validée et sanitée
```

## Content Filter — Seconde Ligne de Défense

**Fichier** : [`app/security/content_filter.py`](../app/security/content_filter.py)

Vérifie que le contenu généré par le LLM respecte les politiques de contenu.

### Catégories de détection

| Catégorie | Patterns détectés |
|-----------|-------------------|
| **Toxicité** | `hate`, `kill`, `murder`, `suicide`, `bomb`, `terrorist`, `extremist`, `racist`, `sexist` |
| **Contenu sexuel** | `sexual`, `porn`, `explicit`, `nude`, `naked` |
| **Violence** | `violence`, `torture`, `abuse`, `assault`, `weapon` |
| **Auto-mutilation** | `hurt myself`, `end my life`, `kill myself`, `self harm`, `suicidal`, `don't want to live` |

### Résultat

- **Contenu sûr** : Retourne `is_safe=True` avec le contenu original
- **Contenu flagué** : Retourne `is_safe=False` avec un message de remplacement : *"I cannot provide that information. Please ask something else."*

### Support batch

La méthode `check_batch(contents)` permet de vérifier plusieurs contenus en une seule opération.

## Output Filter — Troisième Ligne de Défense

**Fichier** : [`app/security/output_filter.py`](../app/security/output_filter.py)

Valide et formate la réponse finale avant qu'elle ne soit envoyée à l'utilisateur.

### Sanitisation Markdown

| Type de contenu | Action |
|-----------------|--------|
| Tags HTML (`<[^>]+>`) | Supprimés |
| Data URIs (`data:[^;]+;base64,...`) | Remplacés par `[removed]` |
| Liens JavaScript (`javascript:[^\s]+`) | Supprimés |

### Vérification des citations

Les citations au format `[1]`, `[2]`, etc. sont vérifiées contre les sources disponibles. Les citations référençant des sources inexistantes sont supprimées.

### Limitations

| Paramètre | Valeur |
|-----------|--------|
| Longueur maximale de réponse | 4000 caractères |
| Nombre maximum de sources | 5 |

### Validation JSON

La méthode `validate_json_response()` extrait et valide les structures JSON dans le contenu, utile pour les réponses structurées.

### Formatage des erreurs

La méthode `format_error()` convertit les erreurs techniques en messages utilisateur conviviaux :

| Code erreur | Message utilisateur |
|-------------|---------------------|
| `rate_limit` | "Too many requests. Please wait a moment." |
| `timeout` | "Request timed out. Please try again." |
| `service_error` | "Service temporarily unavailable." |
| `invalid_input` | "Invalid input. Please check your query." |

## Flux de Défense Complet

```
Requête utilisateur
    │
    ▼
┌──────────────────┐
│   Input Guard    │ ←─ 8 patterns injection, 3 patterns PII
└────────┬─────────┘
         │ query validée
         ▼
┌──────────────────┐
│  RAG Pipeline    │ ←─ Traitement principal
└────────┬─────────┘
         │ réponse brute
         ▼
┌──────────────────┐
│ Content Filter   │ ←─ Toxicité, sexual, violence, self-harm
└────────┬─────────┘
         │ réponse sécurisée
         ▼
┌──────────────────┐
│  Output Filter   │ ←─ Sanitisation, citations, longueur
└────────┬─────────┘
         │ réponse formatée
         ▼
Réponse à l'utilisateur
```

## Modèles de Données Associés

**Fichier** : [`app/models.py`](../app/models.py)

| Modèle | Contenu |
|--------|---------|
| `GuardResult` | `is_valid`, `sanitized_query`, `reason` |
| `ContentFilterResult` | `is_safe`, `sanitized_content`, `flags` |

## Bonnes Pratiques

1. **Défense en profondeur** : Trois couches indépendantes assurent qu'une faille dans une couche est compensée par les autres
2. **Fail-safe** : En cas de doute, le contenu est bloqué plutôt que laissé passer
3. **Logging** : Toutes les détections (injections, PII, contenus flagués) sont journalisées avec `structlog`
4. **Non-exposition des détails** : Les messages d'erreur ne révèlent pas les patterns de détection
5. **Redaction plutôt que blocage** : Les PII sont remplacées plutôt que de bloquer la requête entière

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide des Services](guide-services.md) — Pipeline RAG protégé par la sécurité
- [Guide des Tests](guide-tests.md) — Tests de sécurité (à implémenter)
