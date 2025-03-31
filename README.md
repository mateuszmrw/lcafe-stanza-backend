## Overview

This backend service provides text processing and tokenization capabilities for the LinguaCafe project using the Stanza NLP library. It processes text from ebooks and other sources to extract linguistic features like lemmas, parts of speech, and gender information.

It should work as drop-in replacement for the standard Python LinguaCafe backend, supporting majority of Python backend features - currently only handling subtitles is missing, planned in future.

Example of usage is available in docker-compose.yaml file in root of repo.

Currently CUDA support is not tested since I do not have a GPU that supports it.

The backend service is built with FastAPI and provides a REST API for text processing. It can be run standalone or as part of the full LinguaCafe stack using Docker Compose.

Key features:
- FastAPI REST API endpoints for text processing
- Configurable language model loading
- Efficient resource management through singleton pattern
- Automatic model downloading

Warning: Stanza is way more resource heavy than SpaCy, that comes by default with LinguaCafe project. I would not recommend trying it out without fast machine.

## Features

- Supports English, Polish and Russian languages
- Tokenizes text and extracts linguistic features:
  - Word forms
  - Lemmas
  - Parts of speech
  - Gender (where available)

## Components

### Book Parser
- Handles EPUB file processing
- Extracts and cleans text content
- Supports different chapter sorting methods (spine-based or default)

### Text Parser  
- Breaks text into chunks of configurable size
- Preserves sentence boundaries
- Handles various sentence endings and special characters

### Tokenizer
- Processes text using Stanza models
- Extracts linguistic features
- Returns structured token information

### Stanza Client
- Manages Stanza language models
- Handles model downloading and loading
- Implements singleton pattern for resource efficiency

## Setup

The backend requires Stanza language models for the supported languages. Models will be automatically downloaded when first needed.

## Supported Languages

Currently supports:
- English
- Polish 
- Russian

Each language uses the following Stanza processors:
- tokenize
- pos (Part of Speech)
- lemma
