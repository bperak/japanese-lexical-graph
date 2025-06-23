<!-- 
**Formatting Note:**
This document follows the structural guidelines (sections, abstract, keywords) from the JSET template. 
Final formatting (e.g., Times New Roman/Century fonts, two-column layout) must be applied when converting this Markdown to the final PDF document.
The final manuscript is limited to 2 pages.
-->

# Developing a Method for Teaching Japanese Using Lexical Networks and AI-Based Interactions

**Perak Benedikt*1, Špica Dragana*2**, Atsushi Mori*3**
*University of Rijeka, Faculty of Humanities and Social Sciences*1
*University of Pula, Faculty of Humanities*2

## Abstract

This paper introduces a novel methodology for Japanese language education that combines interactive lexical networks with AI-driven pedagogical features. The complexity of Japanese vocabulary, with its intricate system of synonyms and semantic relationships, presents a significant challenge for learners. We have developed an interactive tool that visualizes these relationships in a 3D graph, enhanced with AI-powered analysis from large language models for term explanations and comparisons. We further propose a system for validating the proficiency level of learning materials and a user-adaptive model to personalize the educational experience, addressing key gaps in computer-assisted language learning.

**Keywords**: *Lexical Networks, AI in Education, Japanese Language, User Modeling*

## 1. Introduction

The acquisition of a robust vocabulary is fundamental to mastering any foreign language, and this is particularly true for Japanese, where a single concept may be expressed through a variety of nuanced terms. Traditional learning methods often present vocabulary in a linear fashion, failing to capture the complex, network-like structure of a lexicon (Perak & Ban Kirigin, 2023). This can make it difficult for learners to grasp the subtle distinctions between synonyms and the broader semantic relationships that define the language.

To address this challenge, we have developed an interactive, web-based platform that visualizes the Japanese lexicon as a dynamic 3D force-directed graph. This approach allows learners to move beyond rote memorization and explore the lexical landscape in an intuitive, non-linear manner. Our work builds on recent advancements in using large language models (LLMs) to enrich and expand lexical networks (Špica & Perak, 2024), integrating Google's Gemini API to provide on-demand, AI-powered analysis. This includes detailed explanations of terms, semantic comparisons, and the generation of contextual learning exercises.

This paper details the architecture of our system and its core features. Furthermore, it introduces two key methodological proposals: a technique for cross-validating the difficulty of AI-generated learning content against an objective readability assessment, and an architecture for a user-adaptive model that can personalize the learning pathway. Together, these components form a comprehensive, AI-enhanced tool designed to make the complexities of the Japanese lexicon more accessible and manageable for learners.

## 2. System Architecture

The system is designed with a client-server architecture. The backend, built with Python, serves a RESTful API and the frontend web application. The frontend is an interactive single-page application that allows users to visualize and interact with the lexical data. This architecture clearly separates the data processing and business logic from the presentation layer, enabling modular development and scalability.

### 2.1. Backend Architecture

The backend is developed using Flask (Pallets, 2024), a lightweight Python web framework. Its primary responsibility is to handle API requests, manage the graph data, and integrate with external services. The core of the application is a large-scale Japanese lexical graph, which is managed using the NetworkX library (Hagberg et al., 2008). The graph, containing nodes (terms) and edges (relationships), is loaded from a serialized Python pickle file at startup, allowing for fast in-memory access and traversal during runtime.

### 2.2. Frontend Architecture

The frontend is a single-page application built with standard web technologies (HTML, CSS, and JavaScript). The central feature is the interactive 3D visualization of the lexical network, which is rendered using the Three.js library (Cabello, n.d.) and the `3d-force-graph` component by Vasco Vasturiano (2018). This visualization employs a force-directed graph layout, enabling users to intuitively explore the complex relationships between Japanese lexical items. User interactions, such as searching for terms or clicking on nodes, trigger API requests to the backend to fetch relevant data, which is then dynamically displayed.

### 2.3. External API Integration

To enrich the lexical data, the system integrates with two key external services. Firstly, it connects to Wikidata's SPARQL endpoint to fetch structured semantic information about Japanese terms, providing users with richer contextual data. Secondly, it leverages the Google Gemini API (Gemini Team et al., 2023) to provide advanced AI-powered features, including AI-generated explanations of terms, semantic comparisons between two selected terms, and the generation of interactive learning exercises. The system is designed to be flexible, allowing for the selection of different Gemini models to balance performance and capability based on the specific task.

## 3. Core Methodologies & Features

The platform integrates several key features to create a comprehensive learning environment.

### 3.1. Interactive 3D Graph Visualization

The core of the user experience is the 3D visualization of the lexical network, designed to be both intuitive and information-rich. This interactive graph allows learners to see the connections between words, including synonyms, antonyms, and other semantic relationships. Key interactive features include:
- **Node Highlighting and Exploration**: Clicking on a node highlights it in a distinct color and also illuminates its immediate neighbors and the links connecting them. This allows users to easily trace direct relationships and explore the local lexical environment of a term.
- **Dynamic Coloring and Styling**: To enhance readability, nodes are dynamically colored based on their part-of-speech (e.g., nouns in green, verbs in blue), providing an at-a-glance grammatical context. Links are also styled by relationship type, with antonyms rendered in a distinct color to differentiate them from synonyms.
- **Search and Focus**: A search function allows users to find specific terms within the graph. The results are highlighted, and an optional "focus" mode automatically zooms and centers the camera on the selected node, making it easy to locate terms in a dense network.
- **Customizable Layout and Filtering**: Users can dynamically switch the force-directed layout between 2D and 3D modes. Additionally, they can filter the display by relationship type, such as toggling the visibility of synonyms or antonyms, to reduce visual clutter and focus on specific types of connections.
- **Detailed Information on Demand**: Interacting with a node (e.g., clicking it) populates a suite of side panels with contextual information, including structured data from Wikidata, AI-generated explanations from the Gemini API, and a detailed list of its neighbors, turning the graph into a rich research tool.

This combination of features provides an exploratory and discovery-oriented learning experience that moves beyond static vocabulary lists.

### 3.2. AI-Powered Lexical Analysis

Leveraging the reasoning capabilities of the Gemini API, the tool offers on-demand analysis of lexical items. When a user selects a term, they can request an AI-generated explanation that provides context, usage examples, and nuances. Furthermore, users can select two nodes (terms) and request a comparative analysis, which explains the subtle differences in meaning and connotation, a feature particularly useful for advanced learners.

### 3.3. Interactive Language Learning Module

To move from passive observation to active practice, the system includes a module for generating interactive learning exercises on demand. When a user selects a term from the graph, they can request the AI to create a custom exercise. This process is driven by dynamically generated prompts sent to the Google Gemini API, which instructs the AI to act as a specialized Japanese language tutor.

The prompts are carefully constructed to include the target word, its metadata (e.g., hiragana, translation), and a list of semantically related terms from the graph to ensure the content is contextually rich. The module supports several key features:
- **Diverse Exercise Types**: The system can generate various types of exercises, including contextual fill-in-the-blank questions, multiple-choice quizzes, and conversational scenarios that use the selected term in a realistic dialogue.
- **Targeted Proficiency Levels**: The generation process is tailored to different proficiency levels. The prompt sent to the Gemini API includes level-specific instructions: beginner-level prompts enforce simple grammar and full English translations, while advanced-level prompts request nuanced cultural references and idiomatic expressions with minimal translation.
- **Interactive Submission and Feedback Loop**: The generated exercises are presented in an interactive panel where users can input their answers. This user response is captured and can be sent back to the server, forming the basis of the feedback and validation loop described in the proficiency validation method (Section 3.5). This transforms the module from a simple content generator into an active learning tool.

This user-centered generation process ensures that the learning content is always relevant to the learner's current focus within the lexical network.

#### 3.3.1. Prompting and Exercise Examples

To illustrate the process, consider a user selecting the node for 「旅行」 (ryokou - travel). The system constructs a detailed prompt for the Gemini API. While the exact prompt is dynamic, its core structure can be summarized as follows:

***
**Prompt Template:**

*   **Role:** "You are a Japanese language teacher specializing in engaging, interactive learning."
*   **Task:** "Create a [lexical exercise | conversational scenario] for a [Beginner | Intermediate | Advanced] level student."
*   **Target Word:** 「旅行」 (ryokou) - travel.
*   **Contextual Words (from graph):** 「ホテル」(hoteru - hotel), 「計画」(keikaku - plan), 「飛行機」(hikouki - airplane).
*   **Instructions (Intermediate Level):** "Use polite grammar (ます/です form). The exercise should test the understanding of 「旅行」 in context. Provide one correct and two plausible incorrect answers."
***

This structured prompt leads to the generation of targeted, context-aware content. Below are two examples of potential outputs.

**Example 1: Intermediate Lexical Exercise**

*Fill in the blank with the most appropriate word:*

来年の夏、ヨーロッパへ＿＿＿を計画しています。
(Rainen no natsu, Yōroppa e ___ o keikaku shite imasu.)

A) 仕事 (shigoto)
B) 勉強 (benkyō)
C) 旅行 (ryokou)

*Correct Answer: C*

**Example 2: Advanced Conversational Scenario**

*A short dialogue using the word 「旅行」:*

**A-san:** 今度の休みにどこかへ旅行する予定はありますか？
(Kondo no yasumi ni dokoka e ryokou suru yotei wa arimasu ka?)
**B-san:** はい、京都へ一人旅行をしようと思っています。古いお寺を見るのが楽しみです。
(Hai, Kyōto e hitori ryokō o shiyō to omotte imasu. Furui otera o miru no ga tanoshimi desu.)

***

These examples demonstrate how the system moves beyond simple definitions to create practical, interactive learning opportunities directly tied to the user's exploration of the lexical graph.

### 3.4. Japanese Readability Assessment

To provide learners and educators with an objective measure of text difficulty, the system incorporates a Japanese readability assessment module. This feature is crucial for selecting appropriate learning materials and for the planned proficiency validation system described in Section 4.1.

The assessment is implemented using the Python `jreadability` library, which analyzes a given text to compute a readability score. The process begins by passing the text to a morphological analyzer (`fugashi`, a wrapper for MeCab), which breaks it down into its constituent words (morphemes) and identifies their parts of speech. Based on this linguistic data—likely analyzing factors such as sentence length, the ratio of complex words (e.g., kanji vs. hiragana), and vocabulary difficulty—the library calculates a numerical score.

This score is then mapped to one of six clear, intuitive proficiency levels, providing an immediate understanding of the text's difficulty:
-   Lower-elementary
-   Upper-elementary
-   Lower-intermediate
-   Upper-intermediate
-   Lower-advanced
-   Upper-advanced

This automated assessment allows the system to quickly classify the complexity of a text. The requirement for at least 500 characters is a key factor in ensuring the reliability of this score. Readability formulas, including the one used by the `jreadability` library, are statistical in nature. They rely on averages of features like sentence length, word difficulty, and character types. With shorter texts, these averages can be easily skewed by a few unusually long sentences or complex words, leading to a volatile and unreliable score. By enforcing a minimum text length, the system ensures a large enough sample size for the statistical analysis to be meaningful, providing a more stable and accurate measure of the content's true cognitive load on a learner. This makes the tool valuable for providing consistent feedback for curriculum development and adaptive learning.

### 3.5. Proficiency Level Validation (Proposed Method)

A significant challenge in AI-generated educational content is ensuring its pedagogical appropriateness. We propose a method to validate the proficiency level of the content produced by the Interactive Language Learning Module. This method creates a feedback loop: first, an exercise is generated by the AI for a target proficiency level. The textual content of this exercise is then programmatically sent to the Japanese Readability Assessment endpoint. The resulting readability score is compared against the intended difficulty level. If there is a mismatch, the prompt used to generate the exercise can be automatically refined and the content regenerated, ensuring that the material is well-suited for the learner.

## 4. User-Adaptive Personalization

To create a truly personalized learning experience, we propose an architecture for a user-adaptive model. This system would extend the current application by introducing user profiles that track and store interaction data. The model would log key user activities, including search queries, viewed nodes, performance on interactive exercises, and AI-generated content requests.

This data would be used to build a dynamic model of the user's knowledge, identifying areas of strength and weakness within the lexical network. Based on this profile, the system could proactively recommend new terms or concepts for exploration, tailor the difficulty of the learning exercises, and highlight connections in the graph that are most relevant to the user's learning trajectory. This transforms the tool from a passive repository of information into an active, intelligent tutor that guides the user through the complexities of the Japanese lexicon.

## 5. Conclusion

In this paper, we have presented a novel, AI-enhanced tool for Japanese language education that leverages the power of lexical networks to create a more intuitive and effective learning experience. By visualizing the complex relationships between words in an interactive 3D graph and integrating AI for on-demand analysis and exercise generation, our platform addresses a key challenge in vocabulary acquisition.

The primary contributions of this work are twofold. First, we have demonstrated the successful implementation of a system that combines graph visualization with the capabilities of modern large language models. Second, we have proposed two significant methodological enhancements: a feedback loop for validating the proficiency level of AI-generated content and an architecture for a user-adaptive model that enables true personalization. These proposed systems outline a clear path toward developing more intelligent and pedagogically sound computer-assisted language learning tools. Future work will focus on implementing and evaluating these proposed systems, expanding the learning modules, and exploring the potential of migrating the graph data to a dedicated graph database to further enhance scalability and performance.

## References

Cabello, R. (n.d.). *Three.js*. Retrieved from https://threejs.org

Gemini Team, et al. (2023). *Gemini: A Family of Highly Capable Multimodal Models*. arXiv:2312.11805.

Hagberg, A. A., Schult, D. A., & Swart, P. J. (2008). Exploring network structure, dynamics, and function using NetworkX. In *Proceedings of the 7th Python in Science Conference (SciPy2008)* (pp. 11–15).

Pallets. (2024). *Flask* (Version 3.0.3) [Computer software]. https://palletsprojects.com/p/flask/

Perak, Benedikt; Ban Kirigin, Tajana. (2023). Construction Grammar Conceptual Network: Coordination-based graph method for semantic association analysis. *Natural Language Engineering*, *29*(3), 584-614. doi: 10.1017/S1351324922000274

Špica, Dragana; Perak, Benedikt. (2024). Enhancing Japanese Lexical Networks Using Large Language Models: Extracting Synonyms and Antonyms with GPT-4o. In K. Štrkalj Despot, A. Ostroški Anić, & I. Brač (Eds.), *Lexicography and Semantics: Proceedings of the XXI EURALEX International Congress* (pp. 265-284). Zagreb: Institut za hrvatski jezik.

Vasturiano, V. (2018). *3d-force-graph*. GitHub. Retrieved from https://github.com/vasturiano/3d-force-graph 

Watanabe, A., Murakami, S., Miyazawa, A., Goto, K., Yanase, T., Takamura, H., & Miyao, Y. (2017). TRF: A Tool for Analyzing Text Readability. In *Proceedings of the 23rd Annual Meeting of the Association for Natural Language Processing* (pp. 477-480).