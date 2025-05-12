from datetime import datetime
from collections import defaultdict
from rich.console import Console
import requests

console = Console()
def get_planned_dates(journal_id, cookie):
    """Fetch lesson entry data from Tahvel API."""
    headers = {
        'Cookie': cookie
    }
    url = f'https://tahvel.edu.ee/hois_back/journals/{journal_id}/journalEntry/lessonInfo'
    
    with console.status("[bold green]Fetching planned dates...[/bold green]") as status:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
    planned_dates = response.json().get('lessonPlanDates', [])
    console.print(f"[bold cyan]Fetched {len(planned_dates)} planned lesson dates.[/bold cyan]")
    
    return planned_dates


def get_journal_entries(journal_id, cookie):
    """Fetch journal entries from Tahvel API and handle pagination."""
    headers = {
        'Cookie': cookie
    }
    url = f'https://tahvel.edu.ee/hois_back/journals/{journal_id}/journalEntry'
    params = {
        'lang': 'ET',
        'page': 0,
        'size': 50
    }
    
    console.print("[bold blue]Fetching journal entries...[/bold blue]")
    
    all_entries = []
    page_count = 0
    
    with console.status("[bold green]Loading data...[/bold green]") as status:
        while True:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            page_content = data.get('content', [])
            all_entries.extend(page_content)
            
            page_count += 1
            status.update(f"[bold green]Loaded page {page_count} ({len(page_content)} entries)[/bold green]")
            
            # Check if there are more pages
            if data.get('last', True):
                break
            
            # Increment page number for the next request
            params['page'] += 1
    
    console.print(f"[bold cyan]Fetched {len(all_entries)} journal entries across {page_count} pages.[/bold cyan]")
    
    return all_entries


def process_planned_dates(planned_dates):
    """Process planned dates into a structured format."""
    date_map = defaultdict(list)
    
    for entry in planned_dates:
        date_obj = datetime.fromisoformat(entry.replace('Z', '+00:00'))
        date_str = date_obj.strftime('%Y-%m-%d')
        time_str = date_obj.strftime('%H:%M:%S')
        
        date_map[date_str].append(time_str)
    
    # Sort times within each date
    for date in date_map:
        date_map[date] = sorted(date_map[date])
    
    # Convert to regular dict and sort by date
    return dict(sorted(date_map.items()))

def process_journal_entries(journal_entries):
    """Process journal entries into a structured format by date."""
    entry_map = {}
    
    for entry in journal_entries:
        if 'entryDate' not in entry:
            continue
            
        try:
            date_obj = datetime.fromisoformat(entry['entryDate'].replace('Z', '+00:00'))
            date_str = date_obj.strftime('%Y-%m-%d')
            
            lessons_count = entry.get('lessons', 0)
            content = entry.get('content', 'N/A')
            
            # Truncate content if it's too long
            if content and len(content) > 40:
                content = content[:37] + "..."
            
            if date_str not in entry_map:
                entry_map[date_str] = {
                    'entries': [],
                    'total_lessons': 0,
                    'content': content
                }
            
            entry_map[date_str]['entries'].append(entry)
            entry_map[date_str]['total_lessons'] += lessons_count
            
        except (ValueError, TypeError):
            continue
    
    return dict(sorted(entry_map.items()))

def compare_entries(planned_dates_map, journal_entries_map):
    """Compare planned dates with journal entries to find matches and mismatches."""
    comparison_results = {}
    
    # Process all planned dates
    for date, times in planned_dates_map.items():
        journal_data = journal_entries_map.get(date, {})
        
        comparison_results[date] = {
            'planned_lessons': len(times),
            'entered_lessons': journal_data.get('total_lessons', 0),
            'content': journal_data.get('content', 'N/A'),
            'times': times,
            'all_inserted': journal_data.get('total_lessons', 0) >= len(times),
            'has_journal_entry': date in journal_entries_map
        }
    
    # Add journal entries that don't have corresponding planned dates
    for date in journal_entries_map:
        if date not in comparison_results:
            journal_data = journal_entries_map[date]
            comparison_results[date] = {
                'planned_lessons': 0,
                'entered_lessons': journal_data.get('total_lessons', 0),
                'content': journal_data.get('content', 'N/A'),
                'times': [],
                'all_inserted': False,
                'has_journal_entry': True
            }
    
    return dict(sorted(comparison_results.items()))


def get_study_years(cookie):
    """Fetch study years from Tahvel API."""
    url = 'https://tahvel.edu.ee/hois_back/autocomplete/studyYears'

    headers = {'Cookie': cookie}

    with console.status("[bold green]Loading study years...[/bold green]") as status:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
    return response.json()


def get_journals(study_year_id, cookie):
    """Fetch all journals for a given study year from Tahvel API."""
    headers = {'Cookie': cookie}
    url = 'https://tahvel.edu.ee/hois_back/journals'
    params = {
        'lang': 'ET',
        'onlyMyJournals': 'true',
        'page': 0,
        'size': 50,
        'sort': '2,+5,+3,asc',
        'studyYear': study_year_id
    }

    console.print("[bold blue]Fetching journals...[/bold blue]")
    journals = []

    with console.status("[bold green]Loading journals...[/bold green]") as status:
        while True:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            journals.extend(data.get('content', []))

            if data.get('last', True):
                break

            params['page'] += 1
            
    console.print(f"[bold cyan]Found {len(journals)} journals.[/bold cyan]")
    return journals
