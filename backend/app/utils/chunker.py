import re
from typing import List, Dict, Any

class IntelligentChunker:
    @staticmethod
    def chunk_text(
        text: str, 
        document_id: int, 
        max_chunk_size: int = 1000, 
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Chunks text by preserving paragraph, section, heading, and sentence boundaries.
        Includes metadata (like page number and current heading) for each chunk.
        """
        # If the text has page markers like [PAGE_1], [PAGE_2], etc., we parse them.
        # Otherwise we assume page_number = 1.
        pages = IntelligentChunker._split_by_pages(text)
        
        chunks = []
        for page_num, page_content in pages:
            # Detect paragraphs / logical blocks
            # We split by double newlines or heading indicators
            blocks = re.split(r'(?=\n(?:#+\s|[A-Z\s]{4,}:?\n))|\n\n', page_content)
            
            current_chunk = ""
            current_heading = "General"
            
            for block in blocks:
                block = block.strip()
                if not block:
                    continue
                
                # Check if block looks like a heading (e.g. Starts with # or is short and all-caps)
                is_heading = block.startswith('#') or (len(block) < 60 and block.isupper() and len(block) > 3)
                if is_heading:
                    current_heading = block.lstrip('# ').strip()
                
                # If adding this block exceeds the max chunk size, we flush the current chunk
                if len(current_chunk) + len(block) > max_chunk_size:
                    if current_chunk:
                        chunks.append({
                            "document_id": document_id,
                            "page_number": page_num,
                            "content": current_chunk.strip(),
                            "chunk_metadata": {
                                "heading": current_heading,
                                "length": len(current_chunk.strip())
                            }
                        })
                    
                    # Start next chunk. If block is too large, split by sentences.
                    if len(block) > max_chunk_size:
                        sub_blocks = IntelligentChunker._split_by_sentences(block, max_chunk_size, overlap)
                        for sb in sub_blocks[:-1]:
                            chunks.append({
                                "document_id": document_id,
                                "page_number": page_num,
                                "content": sb.strip(),
                                "chunk_metadata": {
                                    "heading": current_heading,
                                    "length": len(sb.strip())
                                }
                            })
                        current_chunk = sub_blocks[-1]
                    else:
                        # Add block with overlap from previous chunk if possible
                        overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
                        current_chunk = (overlap_text + "\n" + block).strip()
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + block
                    else:
                        current_chunk = block
            
            # Flush the final chunk of the page
            if current_chunk:
                chunks.append({
                    "document_id": document_id,
                    "page_number": page_num,
                    "content": current_chunk.strip(),
                    "chunk_metadata": {
                        "heading": current_heading,
                        "length": len(current_chunk.strip())
                    }
                })
                
        return chunks

    @staticmethod
    def _split_by_pages(text: str) -> List[tuple[int, str]]:
        """
        Splits text based on injected page markers. e.g. [PAGE_1], [PAGE_2].
        Returns list of (page_number, text).
        """
        page_pattern = r'\[PAGE_(\d+)\]'
        matches = list(re.finditer(page_pattern, text))
        
        if not matches:
            return [(1, text)]
            
        pages = []
        for i in range(len(matches)):
            start_idx = matches[i].end()
            end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
            page_num = int(matches[i].group(1))
            page_text = text[start_idx:end_idx]
            pages.append((page_num, page_text))
            
        return pages

    @staticmethod
    def _split_by_sentences(text: str, max_size: int, overlap: int) -> List[str]:
        """
        Helper to split large text block into overlapping chunks at sentence boundaries.
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sub_chunks = []
        current_sub = ""
        
        for sent in sentences:
            if len(current_sub) + len(sent) > max_size:
                if current_sub:
                    sub_chunks.append(current_sub)
                
                # Handle single sentence longer than max_size
                if len(sent) > max_size:
                    # Hard break by character
                    for i in range(0, len(sent), max_size - overlap):
                        sub_chunks.append(sent[i:i + max_size])
                    current_sub = ""
                else:
                    overlap_text = current_sub[-overlap:] if len(current_sub) > overlap else ""
                    current_sub = (overlap_text + " " + sent).strip()
            else:
                if current_sub:
                    current_sub += " " + sent
                else:
                    current_sub = sent
                    
        if current_sub:
            sub_chunks.append(current_sub)
            
        return sub_chunks
