# Index Configuration

This directory contains vector store index configurations.

## Files

- `collections.json` - ChromaDB collection definitions
- `metadata_schema.json` - Document metadata schema
- `embedding_config.json` - Embedding model configuration

## Example Collection Config

```json
{
  "collections": [
    {
      "name": "documents",
      "embedding_model": "text-embedding-3-small",
      "metadata": {
        "description": "Main document collection"
      }
    },
    {
      "name": "code",
      "embedding_model": "text-embedding-3-small",
      "metadata": {
        "description": "Code snippets collection"
      }
    }
  ]
}
```
