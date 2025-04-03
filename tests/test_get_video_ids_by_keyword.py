import logging

keywords = ['python', 'data science', 'machine learning']
max_results = 100

def get_video_ids_by_keywords(keywords,max_results ):
    """
    Retrieve YouTube video IDs based on multiple keywords.
    
    Args:
        context: Airflow context containing params with 'keywords' and 'max_results'
        
    Returns:
        list: List of YouTube video IDs from all keywords
    """
    import yt_dlp as youtube_dlp
    from tqdm import tqdm
    
    # Lấy tham số từ context
    
    # Đảm bảo keywords là danh sách
    if isinstance(keywords, str):
        keywords = [keywords]
    
    logging.info(f"Tìm kiếm video cho {len(keywords)} từ khóa: {keywords}")
    
    all_video_ids = []
    max_per_keyword = max(max_results // len(keywords), 10)  # Phân bổ số lượng kết quả trên mỗi từ khóa
    
    for keyword in keywords:
        try:
            # Tạo URL tìm kiếm trên YouTube
            search_query = f"ytsearch{max_per_keyword}:{keyword}"
            
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': True,
                'ignoreerrors': True,
            }
            
            logging.info(f"Đang tìm kiếm với từ khóa: '{keyword}'")
            
            with youtube_dlp.YoutubeDL(ydl_opts) as ydl:
                results = ydl.extract_info(search_query, download=False)
                
                if 'entries' in results:
                    for entry in results['entries']:
                        if entry and 'id' in entry:
                            video_id = entry['id']
                            if video_id not in all_video_ids:  # Tránh trùng lặp
                                all_video_ids.append(video_id)
                
                logging.info(f"Đã tìm thấy {len(all_video_ids)} video (tổng số) sau khi tìm kiếm '{keyword}'")
                
                # Dừng nếu đã đủ số lượng kết quả cần thiết
                if len(all_video_ids) >= max_results:
                    break
                    
        except Exception as e:
            logging.error(f"Lỗi khi tìm kiếm với từ khóa '{keyword}': {str(e)}")
            continue
    
    # Giới hạn kết quả theo max_results
    all_video_ids = all_video_ids[:max_results]

    return all_video_ids
video_ids = get_video_ids_by_keywords(keywords=keywords, max_results=max_results)
print(video_ids)
print(len(video_ids))