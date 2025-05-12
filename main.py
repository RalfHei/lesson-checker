from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt
import argparse
import os
import pickle
import requests

from tahvel import compare_entries, get_journal_entries, get_planned_dates, process_journal_entries, process_planned_dates, get_journals, get_study_years, get_journal_details

# Make sure rich is installed
# If not installed, run: pip install rich

console = Console()
CONFIG_DIR = os.path.expanduser("~/.tahvel-checker")
COOKIE_FILE = os.path.join(CONFIG_DIR, "cookies.pickle")

def display_study_years(study_years):
    """Display available study years for selection."""
    table = Table(title="Available Study Years", border_style="blue")
    table.add_column("Option", style="cyan", justify="center")
    table.add_column("Year", style="green")
    table.add_column("ID", style="yellow")
    
    for i, year in enumerate(study_years, 1):
        table.add_row(str(i), year.get('nameEt', 'Unknown'), str(year.get('id', 'N/A')))
    
    console.print(table)
    return {i: year for i, year in enumerate(study_years, 1)}

def display_journals(journals):
    """Display available journals for selection."""
    table = Table(title="Available Journals", border_style="green")
    table.add_column("Option", style="cyan", justify="center")
    table.add_column("Name", style="green")
    table.add_column("ID", style="yellow")
    
    for i, journal in enumerate(journals, 1):
        table.add_row(str(i), journal.get('nameEt', 'Unknown'), str(journal.get('id', 'N/A')))
    
    console.print(table)
    return {i: journal for i, journal in enumerate(journals, 1)}

def process_journal(journal_id, cookie):
    """Process a single journal and display its results."""
    # Display title
    console.print(Panel(f"[bold green]Tahvel Lesson Completion Checker - Journal ID: {journal_id}[/bold green]", 
                        border_style="blue", 
                        expand=False))
    
    try:
        # Get data
        planned_dates = get_planned_dates(journal_id, cookie)
        journal_entries = get_journal_entries(journal_id, cookie)
        journal_details = get_journal_details(journal_id, cookie)
        
        # Process data
        planned_dates_map = process_planned_dates(planned_dates)
        journal_entries_map = process_journal_entries(journal_entries)
        
        # Compare data
        comparison_results = compare_entries(planned_dates_map, journal_entries_map)
        
        # Create and display comparison table
        comparison_table, missing_count = create_comparison_table(comparison_results)
        console.print(comparison_table)
        
        # Summary statistics
        total_dates = len(comparison_results)
        complete_dates = total_dates - missing_count
        
        # Get hours information from journal details
        total_planned_hours = journal_details.get('totalPlannedHours', 0)
        capacity_hours = journal_details.get('capacityHours', {})
        
        # Calculate total journal hours
        total_journal_hours = sum(
            hours.get('usedHours', 0) for hours in capacity_hours.values()
        )
        
        # Calculate completion percentage
        completion_percentage = (total_journal_hours / total_planned_hours * 100) if total_planned_hours > 0 else 0
        
        summary = Text.assemble(
            ("Summary\n", "bold magenta"),
            ("Total Dates: ", "bold cyan"), (f"{total_dates}\n", "yellow"),
            ("Complete Dates: ", "bold cyan"), (f"{complete_dates}\n", "green"),
            ("Incomplete Dates: ", "bold cyan"), (f"{missing_count}\n", "red"),
            ("Completion Rate: ", "bold cyan"), 
            (f"{complete_dates/total_dates*100:.1f}%" if total_dates > 0 else "N/A", "yellow"),
            ("\nJournal Hours\n", "bold magenta"),
            ("Total Planned Hours: ", "bold cyan"), (f"{total_planned_hours}\n", "yellow"),
            ("Total Journal Hours: ", "bold cyan"), (f"{total_journal_hours}\n", "green"),
            ("Planned vs Journal Completion: ", "bold cyan"), 
            (f"{completion_percentage:.1f}%\n", "green" if completion_percentage >= 100 else "yellow" if completion_percentage >= 75 else "red")
        )
        
        # Add capacity-specific hours if available
        if capacity_hours:
            for capacity, hours in capacity_hours.items():
                if not isinstance(hours, dict):
                    continue  # Skip if hours is not a dictionary
                
                planned = hours.get('plannedHours', 0)
                used = hours.get('usedHours', 0)
                remaining = planned - used
                completion_percent = (used / planned * 100) if planned > 0 else 0
                
                capacity_label = capacity.split('_')[-1] if '_' in capacity else capacity
                
                summary.append(Text.assemble(
                    (f"Capacity {capacity_label}: ", "bold cyan"),
                    (f"Planned: {planned}, ", "yellow"),
                    (f"Used: {used}, ", "green"),
                    (f"Remaining: {remaining}, ", "blue"),
                    (f"Completion: {completion_percent:.1f}%\n", 
                     "green" if completion_percent >= 100 else "yellow" if completion_percent >= 75 else "red")
                ))
        
        console.print(Panel(summary, border_style="green"))
        
        return True
    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]HTTP Error for journal {journal_id}: {e}[/bold red]")
        if e.response.status_code == 401 or e.response.status_code == 403:
            console.print("[bold yellow]Authentication failed. Your cookie may be expired or invalid.[/bold yellow]")
        return False
    except Exception as e:
        console.print(f"[bold red]Error processing journal {journal_id}: {e}[/bold red]")
        return False


def save_cookie(cookie_value):
    """Save the cookie to a file for persistence."""
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
        with open(COOKIE_FILE, 'wb') as f:
            pickle.dump(cookie_value, f)
        return True
    except Exception as e:
        console.print(f"[bold red]Error saving cookie: {e}[/bold red]")
        return False

def load_cookie():
    """Load the cookie from file if it exists."""
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        console.print(f"[bold yellow]Warning: Could not load saved cookie: {e}[/bold yellow]")
    return None

def create_comparison_table(comparison_results):
    """Create a table showing the comparison results."""
    table = Table(show_header=True, 
                  header_style="bold blue",
                  title="[bold green]Lesson Entries Comparison[/bold green]",
                  border_style="cyan")
    
    table.add_column("Date", style="cyan")
    table.add_column("Content", style="yellow", max_width=40)
    table.add_column("Planned", justify="center", style="magenta")
    table.add_column("Regular (T)", justify="center", style="blue")
    table.add_column("Independent (I)", justify="center", style="green")
    table.add_column("Other", justify="center", style="yellow")
    table.add_column("Complete", justify="center")
    
    missing_count = 0
    
    for date, data in comparison_results.items():
        planned = str(data['planned_lessons'])
        regular = str(data['regular_lessons'])
        independent = str(data['independent_lessons'])
        other = str(data['other_lessons'])
        
        # Get entry type details if available
        entry_types = data.get('entry_types', {})
        entry_type_str = ", ".join([f"{k.split('_')[-1]}:{v}" for k, v in entry_types.items() if k != 'SISSEKANNE_T' and k != 'SISSEKANNE_I'])
        if entry_type_str:
            other_with_details = f"{other} ({entry_type_str})"
        else:
            other_with_details = other
        
        # Determine if all planned lessons are accounted for by regular lessons
        if data['all_inserted']:
            status = "[bold green]✓[/bold green]"
        else:
            status = "[bold red]✗[/bold red]"
            missing_count += 1
        
        table.add_row(
            date,
            data['content'],
            planned,
            regular,
            independent,
            other_with_details,
            status
        )
    
    return table, missing_count

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Tahvel Lesson Completion Checker")
    parser.add_argument("-j", "--journal-id", type=int, help="Journal ID to check (if not provided, will list all available journals)")
    parser.add_argument("-c", "--cookie", type=str, help="Authentication cookie for Tahvel (if not provided, will use saved cookie)")
    parser.add_argument("-s", "--save-cookie", action="store_true", help="Save the provided cookie for future use")
    parser.add_argument("-a", "--all-journals", action="store_true", help="Process all journals for the selected study year")
    parser.add_argument("-y", "--study-year", type=int, help="Study year ID (if not provided, will prompt for selection)")
    
    args = parser.parse_args()
    
    # Get cookie (either from args, saved file, or prompt)
    cookie = load_cookie()
    if not cookie:
        console.print("[bold red]No valid cookie provided. Exiting.[/bold red]")
        return
    
    # Save cookie if requested
    if args.cookie and args.save_cookie:
        save_cookie(args.cookie)
        console.print("[bold green]Cookie saved for future use.[/bold green]")
    
    # If journal ID is provided, process that specific journal
    if args.journal_id:
        process_journal(args.journal_id, cookie)
        return
    
    # Get study years
    try:
        study_years = get_study_years(cookie)
    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]HTTP Error: {e}[/bold red]")
        if e.response.status_code == 401 or e.response.status_code == 403:
            console.print("[bold yellow]Authentication failed. Your cookie may be expired or invalid.[/bold yellow]")
        return
    except Exception as e:
        console.print(f"[bold red]Error fetching study years: {e}[/bold red]")
        return
    
    # Select study year
    study_year_id = None
    
    # If study year ID was provided in arguments
    if args.study_year:
        # Verify the provided study year ID exists
        study_year = next((year for year in study_years if year.get('id') == args.study_year), None)
        if study_year:
            study_year_id = args.study_year
            console.print(f"[bold green]Using specified study year: {study_year.get('nameEt', 'Unknown')} (ID: {study_year_id})[/bold green]")
        else:
            console.print(f"[bold red]The specified study year ID {args.study_year} was not found. Available study years:[/bold red]")
            study_year_map = display_study_years(study_years)
            return
    else:
        # Interactive selection
        study_year_map = display_study_years(study_years)
        if not study_year_map:
            console.print("[bold red]No study years found.[/bold red]")
            return
        
        choice = IntPrompt.ask("Select a study year", choices=[str(i) for i in study_year_map.keys()])
        study_year = study_year_map[choice]
        study_year_id = study_year['id']
    
    # Get journals for the selected study year
    try:
        journals = get_journals(study_year_id, cookie)
    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]HTTP Error: {e}[/bold red]")
        return
    except Exception as e:
        console.print(f"[bold red]Error fetching journals: {e}[/bold red]")
        return
    
    if not journals:
        console.print("[bold red]No journals found for the selected study year.[/bold red]")
        return
    
    # Process all journals or select one
    if args.all_journals:
        console.print(f"[bold blue]Processing all {len(journals)} journals...[/bold blue]")
        success_count = 0
        for journal in journals:
            journal_id = journal.get('id')
            journal_name = journal.get('nameEt', 'Unknown')
            console.print(f"\n[bold cyan]Processing journal: {journal_name} (ID: {journal_id})[/bold cyan]")
            if process_journal(journal_id, cookie):
                success_count += 1
        console.print(f"[bold green]Successfully processed {success_count} out of {len(journals)} journals.[/bold green]")
    else:
        # Interactive journal selection
        journal_map = display_journals(journals)
        if not journal_map:
            console.print("[bold red]No journals found.[/bold red]")
            return
        
        choice = IntPrompt.ask("Select a journal to check", choices=[str(i) for i in journal_map.keys()])
        journal = journal_map[choice]
        journal_id = journal['id']
        
        process_journal(journal_id, cookie)

# Run the application
if __name__ == "__main__":
    main()










