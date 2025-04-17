def extract_content_from_transcript(transcript):
    """
    Trích xuất nội dung có ý nghĩa từ transcript
    
    Args:
        transcript (str): Nội dung transcript từ video
        
    Returns:
        str: Nội dung đã được trích xuất và tóm tắt
    """
    if not transcript or transcript.strip() == "":
        return "Không có nội dung"
    
    # Đây là phiên bản đơn giản, bạn có thể mở rộng với NLP hoặc LLM
    # Ví dụ: Loại bỏ nội dung lặp lại, tóm tắt, phân tích sentiment...
    
    # Xử lý cơ bản: giới hạn độ dài và loại bỏ ký tự đặc biệt
    cleaned_text = transcript.replace('\n', ' ').strip()
    
    # Nếu có nội dung quá dài, có thể tóm tắt ở đây
    max_length = 1000
    if len(cleaned_text) > max_length:
        content = cleaned_text[:max_length] + "..."
    else:
        content = cleaned_text
        
    return content