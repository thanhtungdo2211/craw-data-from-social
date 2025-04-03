from airflow.decorators import task
import logging
from airflow.exceptions import AirflowException
import config

@task.virtualenv(
    requirements=[f"yt-dlp=={config.YT_DLP_VERSION}"],
    system_site_packages=False,
)
def get_video_ids_by_keywords(keywords, max_results) -> list:
    """
    Retrieve YouTube video IDs based on multiple keywords.
    
    Args:
        keywords (list): List of search keywords
        max_results (int): Maximum total results to retrieve
        
    Returns:
        list: List of YouTube video IDs from all keywords
    """
    import yt_dlp as youtube_dlp #type: ignore
    import logging
    
    logging.info(f"Starting search with keywords: {keywords}, max_results: {max_results}")
    
    # Ensure keywords is a list
    if isinstance(keywords, str):
        keywords = [keywords]
    
    all_video_ids = []
    max_per_keyword = max(max_results // len(keywords), 10) if len(keywords) > 0 else max_results
    
    for keyword in keywords:
        try:
            search_query = f"ytsearch{max_per_keyword}:{keyword}"
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': True,
                'ignoreerrors': True,
            }
            
            with youtube_dlp.YoutubeDL(ydl_opts) as ydl:
                results = ydl.extract_info(search_query, download=False)
                if 'entries' in results:
                    for entry in results['entries']:
                        if entry and 'id' in entry:
                            video_id = entry['id']
                            if video_id not in all_video_ids:
                                all_video_ids.append(video_id)
                
            if len(all_video_ids) >= max_results:
                break
                
        except Exception as e:
            logging.error(f"Error searching keyword '{keyword}': {str(e)}")
            continue
    
    all_video_ids = all_video_ids[:max_results]
    return all_video_ids