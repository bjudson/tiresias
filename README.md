# Tiresias

This is a very simple personal project to explore connections in dreams using LLMs. Currently it is configured to use Claude. 

## Philosophy

Terisias is a pretty opinionated project. It was inspired by James Hillman's book [The Dream and the Underworld](https://archive.org/details/dreamunderworld00hill), which encourages letting the dream image have a life of its own, without reducing it to rationalistic interpretation. Terisias calls LLMs to help find connections between dreams on a symbolic level, without relying on the model for meaning making. I explicitly ground the prompts using Hillman, but it would be easy to use the same principles with a different approach to dream exploration. The main thing we avoid is leaning on the model for symbolic analysis, which is reductive, and outsources soul-making.

The challenge with the typical design of off the shelf LLM tools is tracking past insights and incorporating them into new analysis. In Tiresias, symbol files are used to organize the text and layer on meaning.

Ultimately, I hope to uncover patterns that could be helpful for exploring any complex, symbolic text regardless of interpretive framework.

## Functionality

Right now, the system provides these commands:
1. `extract` — extract symbols from a dream file, creating new symbol stubs and tagging the dream
2. `find` — find all dreams that contain a given symbol and aggregate them into a derived file
3. `symbols` — list all symbols ranked by how many dreams they appear in
4. `audit` — scan all dreams for symbol connections the extractor may have missed
5. `rename` — rename a symbol's slug across every dream that references it (merges if the target already exists)
6. `summarize` — generate a summary for a symbol based on the dreams it appears in

All data is stored in flat markdown files with front matter. This just makes it easy to edit the files manually without building a whole UI. 

## Future 

I am interested in adding more search and analysis tools, like using embeddings to find related dreams, having ways to help refine and clarify symbols over time, clustering co-occuring images, etc.
