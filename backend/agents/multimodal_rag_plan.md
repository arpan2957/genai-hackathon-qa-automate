## Multi-modal RAG Implementation Plan

This plan outlines the steps to implement multi-modal Retrieval-Augmented Generation (RAG) within the application, allowing the system to store, retrieve, and utilize both text and image data for enhanced AI context.

**Phase 1: Multi-modal Knowledge Base Storage**

1.  **Extend `KnowledgeBaseDocument` Model (`backend/models.py`):**
    *   Add new fields to the `KnowledgeBaseDocument` Pydantic model to store information about multi-modal assets:
        *   `image_url: Optional[str]` (URL to the image in Google Cloud Storage)
        *   `image_embedding: Optional[List[float]]` (Vector embedding of the image)
        *   `document_type: Literal['text', 'image', 'multimodal']` (To distinguish content types)

2.  **Modify `create_knowledge_base_document` Endpoint (`backend/routers/knowledge_base.py`):**
    *   **Handle Image Uploads:** Update the endpoint to accept image files (e.g., PNG, JPG) in addition to text documents.
    *   **Image Pre-processing and Storage:**
        *   If an image file is uploaded, store the raw image data in a designated Google Cloud Storage (GCS) bucket.
        *   Generate a publicly accessible (or signed) GCS URL for the stored image.
        *   Generate multi-modal embeddings for the image. This will require using a multi-modal embedding model (e.g., `gemini-pro-vision` or a dedicated multi-modal embedding API from Vertex AI).
        *   Store the GCS image URL and its multi-modal embedding in the BigQuery `knowledge_base.documents` table and the Firestore `knowledge_base` collection.
    *   **Handle Multi-modal Document Uploads:** If a document contains both text and images (e.g., a PDF with embedded diagrams), extract both modalities and process them to generate a combined multi-modal embedding.

3.  **Update BigQuery Schema:**
    *   Ensure the BigQuery table (`knowledge_base.documents`) schema is updated to include columns for `image_url` (STRING) and `image_embedding` (ARRAY<FLOAT>) to store the new multi-modal data.

**Phase 2: Multi-modal Retrieval**

1.  **Modify `generate_test_cases` Endpoint (`backend/routers/generation.py`):**
    *   **Multi-modal Query Embedding:** If the `RequirementRequest` contains `image_data` (indicating a multi-modal query from the user), generate a multi-modal embedding for this combined text and image query using a multi-modal embedding model.
    *   **Multi-modal Vector Search:** Use this multi-modal query embedding to perform a vector similarity search in BigQuery. The search should now compare the query embedding against both text embeddings and multi-modal embeddings stored in the `knowledge_base.documents` table.
    *   **Retrieve Multi-modal Context:** Retrieve not just text content, but also image URLs (if available) from the most relevant multi-modal documents found in the knowledge base.

2.  **Update `GenerationAgent` (`backend/agents/generation_agent.py`):**
    *   Modify the `GenerationAgent` to accept and process multi-modal context. This means its methods (e.g., `generate_initial_test_cases`, `refine_test_cases`) should be able to receive both text and image data as part of the context.

**Phase 3: Multi-modal Augmentation**

1.  **Modify `GenerationAgent` (`backend/agents/generation_agent.py`):**
    *   **Multi-modal Prompt Construction:** When constructing the prompt for the Gemini model, include both the retrieved text context and the retrieved image data. For images, this might involve passing image objects (e.g., PIL Image objects loaded from GCS URLs) directly to the multi-modal Gemini model.
    *   **Multi-modal Model Invocation:** Ensure the agent invokes a multi-modal Gemini model (e.g., `gemini-pro-vision` or `gemini-1.5-flash`) when multi-modal context is available, as these models are designed to process both text and image inputs simultaneously.

**Phase 4: Frontend Integration (Optional for initial backend implementation)**

1.  **Update `AiModal` (`frontend/src/components/AiModal.js`):**
    *   Provide UI elements that allow users to upload image files when adding to the knowledge base.
    *   Enhance the generation/refinement prompt input to allow users to include images directly in their queries, which will then trigger the multi-modal RAG retrieval.

**Key Considerations:**

*   **Multi-modal Embedding Model Selection:** Carefully choose the most appropriate multi-modal embedding model from Vertex AI or the Gemini API for optimal performance and cost-efficiency.
*   **Google Cloud Storage (GCS) Integration:** Implement robust GCS integration for secure and efficient storage and retrieval of image assets.
*   **Cost and Performance Monitoring:** Actively monitor the costs associated with multi-modal embedding generation, storage, and model inference, as these can be significantly higher than text-only operations. Optimize where possible.
*   **Complexity Management:** This is a significant architectural and implementation undertaking. Break down the work into smaller, manageable tasks and test thoroughly at each stage.
