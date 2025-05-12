from datetime import datetime
from collections import defaultdict
from rich.console import Console
import requests

console = Console()

def get_entry_types(cookie):
    url = 'https://tahvel.edu.ee/hois_back/autocomplete/classifiers'
    params = {'mainClassCode': 'SISSEKANNE'}
    headers = {'Cookie': cookie}

    with console.status("[bold green]Fetching entry types...[/bold green]") as status:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

    entry_types = response.json()
    codes = [entry['code'] for entry in entry_types]
    console.print(f"[bold cyan]Fetched {len(codes)} entry codes.[/bold cyan]")
    return codes

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

def get_journal_details(journal_id, cookie):
    """Fetch journal details from Tahvel API and retrieve all possible capacities."""
    headers = {
        'Cookie': cookie
    }
    url = f'https://tahvel.edu.ee/hois_back/journals/{journal_id}'
    
    with console.status("[bold green]Fetching journal details...[/bold green]") as status:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
    journal_details = response.json()
    lesson_hours = journal_details.get('lessonHours', {})
    total_planned_hours = lesson_hours.get('totalPlannedHours', 0)
    capacity_hours = lesson_hours.get('capacityHours', [])
    
    all_capacities = {capacity['capacity'] for capacity in capacity_hours}
    differentiated_hours = {
        capacity['capacity']: {
            'plannedHours': capacity.get('plannedHours', 0),
            'usedHours': capacity.get('usedHours', 0)
        }
        for capacity in capacity_hours
    }
    
    console.print(f"[bold cyan]Fetched journal details. Total planned hours: {total_planned_hours}[/bold cyan]")
    console.print(f"[bold cyan]Hours by capacity: {differentiated_hours}[/bold cyan]")
    console.print(f"[bold cyan]All possible capacities: {all_capacities}[/bold cyan]")
    
    return {
        'totalPlannedHours': total_planned_hours,
        'capacityHours': differentiated_hours,
        'allCapacities': all_capacities
    }


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
    """Process journal entries into a structured format by date, categorized by entry type."""
    entry_map = {}
    
    for entry in journal_entries:
        # Ensure 'entryDate' exists and is not None
        entry_date = entry.get('entryDate')
        if not entry_date:
            continue  # Skip entries without a valid date
            
        try:
            # Convert the date to a datetime object
            date_obj = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
            date_str = date_obj.strftime('%Y-%m-%d')
            
            lessons_count = entry.get('lessons', 0)
            content = entry.get('content', 'N/A')
            
            # Handle different formats of entryType (string or dictionary)
            entry_type_data = entry.get('entryType', 'UNKNOWN')
            if isinstance(entry_type_data, dict):
                entry_type = entry_type_data.get('code', 'UNKNOWN')
            else:
                entry_type = entry_type_data  # Use directly if it's a string
            
            # Truncate content if it's too long
            if content and len(content) > 40:
                content = content[:37] + "..."
            
            if date_str not in entry_map:
                entry_map[date_str] = {
                    'entries': [],
                    'total_lessons': 0,
                    'content': content,
                    'regular_lessons': 0,  # SISSEKANNE_T count
                    'independent_lessons': 0,  # SISSEKANNE_I count
                    'other_lessons': 0,  # Other types count
                    'entry_types': {}  # Count by entry type
                }
            
            entry_map[date_str]['entries'].append(entry)
            entry_map[date_str]['total_lessons'] += lessons_count
            
            # Update counts by entry type
            if entry_type == 'SISSEKANNE_T':
                entry_map[date_str]['regular_lessons'] += lessons_count
            elif entry_type == 'SISSEKANNE_I':
                entry_map[date_str]['independent_lessons'] += lessons_count
            else:
                entry_map[date_str]['other_lessons'] += lessons_count
            
            # Track all entry types used
            if entry_type not in entry_map[date_str]['entry_types']:
                entry_map[date_str]['entry_types'][entry_type] = 0
            entry_map[date_str]['entry_types'][entry_type] += lessons_count
            
        except (ValueError, TypeError) as e:
            console.print(f"[dim red]Error processing entry: {e}[/dim red]")
            continue
    
    return dict(sorted(entry_map.items()))

def compare_entries(planned_dates_map, journal_entries_map):
    """Compare planned dates with journal entries to find matches and mismatches.
    Only regular lessons (SISSEKANNE_T) are compared against planned dates."""
    comparison_results = {}
    
    # Process all planned dates
    for date, times in planned_dates_map.items():
        journal_data = journal_entries_map.get(date, {})
        
        # For comparison, we only consider regular lessons (SISSEKANNE_T)
        regular_lessons = journal_data.get('regular_lessons', 0)
        
        comparison_results[date] = {
            'planned_lessons': len(times),
            'entered_lessons': journal_data.get('total_lessons', 0),
            'regular_lessons': regular_lessons,
            'independent_lessons': journal_data.get('independent_lessons', 0),
            'other_lessons': journal_data.get('other_lessons', 0),
            'content': journal_data.get('content', 'N/A'),
            'times': times,
            'entry_types': journal_data.get('entry_types', {}),
            # Only regular lessons should match with planned dates
            'all_inserted': regular_lessons >= len(times),
            'has_journal_entry': date in journal_entries_map
        }
    
    # Add journal entries that don't have corresponding planned dates
    for date in journal_entries_map:
        if date not in comparison_results:
            journal_data = journal_entries_map[date]
            comparison_results[date] = {
                'planned_lessons': 0,
                'entered_lessons': journal_data.get('total_lessons', 0),
                'regular_lessons': journal_data.get('regular_lessons', 0),
                'independent_lessons': journal_data.get('independent_lessons', 0),
                'other_lessons': journal_data.get('other_lessons', 0),
                'content': journal_data.get('content', 'N/A'),
                'times': [],
                'entry_types': journal_data.get('entry_types', {}),
                'all_inserted': True,  # No planned lessons, so it's technically complete
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
