# Tiresias

This is a very simple personal project to explore connections in dreams using LLMs. Currently it is configured to use Claude. 

## Philosophy

Terisias is a pretty opinionated project. I was inspired by James Hillman's book [The Dream and the Underworld](https://archive.org/details/dreamunderworld00hill), and the idea here is to use LLMs to help find connections between dreams on a symbolic level, without relying on the model for interpretation. Hillman's work encourages letting the dream image have a life of its own, without reducing it to rationalistic interpretation. I explicitly ground the prompts using Hillman, but it would be easy to use the same principles with a different approach to dream interpretation. The main thing I want to avoid is leaning on the model for interpretation, which I feel can often be reductive.

The challenge with the typical design of LLM tools is tracking past insights and incorporating them into new analysis. The concept of this project is to extract symbols, and then allow connecting a dream library through repeated symbols.

## Functionality

Right now, all the system really does is:
1. extract symbols from dreams
2. find all dreams that contain a given symbol

All data is stored in flat markdown files with front matter. This just makes it easy to edit the files manually without building a whole UI. 

## Future 

I am interested in adding more search and analysis tools, like using embeddings to find related dreams, having ways to help refine and clarify symbols over time, clustering co-occuring images, etc.
