from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt
import argparse
import os
import pickle
import requests

from tahvel import compare_entries, get_journal_entries, get_planned_dates, process_journal_entries, process_planned_dates, get_journals, get_study_years

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
        
        summary = Text.assemble(
            ("Summary\n", "bold magenta"),
            ("Total Dates: ", "bold cyan"), (f"{total_dates}\n", "yellow"),
            ("Complete Dates: ", "bold cyan"), (f"{complete_dates}\n", "green"),
            ("Incomplete Dates: ", "bold cyan"), (f"{missing_count}\n", "red"),
            ("Completion Rate: ", "bold cyan"), 
            (f"{complete_dates/total_dates*100:.1f}%" if total_dates > 0 else "N/A", "yellow")
        )
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
    table.add_column("Entered", justify="center", style="blue")
    table.add_column("Complete", justify="center")
    
    missing_count = 0
    
    for date, data in comparison_results.items():
        planned = str(data['planned_lessons'])
        entered = str(data['entered_lessons'])
        
        # Determine if all planned lessons are accounted for
        if data['all_inserted']:
            status = "[bold green]✓[/bold green]"
        else:
            status = "[bold red]✗[/bold red]"
            missing_count += 1
        
        table.add_row(
            date,
            data['content'],
            planned,
            entered,
            status
        )
    
    return table, missing_count

def main():
    """Main function to compare planned lessons with actual journal entries."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Check Tahvel journal entries against planned lessons')
    parser.add_argument('--journal-id', '-j', type=str,
                      help='Journal ID to check (if not provided, will list all available journals)')
    parser.add_argument('--cookie', '-c', type=str,
                      help='Authentication cookie for Tahvel (if not provided, will use saved cookie)')
    parser.add_argument('--save-cookie', '-s', action='store_true',
                      help='Save the provided cookie for future use')
    parser.add_argument('--all-journals', '-a', action='store_true',
                      help='Process all journals for the selected study year')
    args = parser.parse_args()
    
    # Handle cookie
    cookie = args.cookie
    if not cookie:
        cookie = load_cookie()
        if not cookie:
            console.print("[bold red]Error: No cookie provided and no saved cookie found.[/bold red]")
            console.print("[bold yellow]Please provide a cookie with the --cookie/-c option.[/bold yellow]")
            console.print("[bold yellow]You can save it for future use with the --save-cookie/-s flag.[/bold yellow]")
            return
    elif args.save_cookie:
        if save_cookie(cookie):
            console.print("[bold green]Cookie saved successfully for future use.[/bold green]")
    
    # If journal ID is provided directly, process that journal only
    if args.journal_id:
        process_journal(args.journal_id, cookie)
        return
        # Otherwise, list study years and journals
    try:
        # Get study years
        console.print("[bold blue]Fetching available study years...[/bold blue]")
        years = get_study_years(cookie)
        if not years:
            console.print("[bold red]No study years found.[/bold red]")
            return
        
        # Display study years and prompt for selection
        year_map = display_study_years(years)
        study_year_choice = IntPrompt.ask(
            "Select a study year (enter the option number)", 
            choices=[str(i) for i in year_map.keys()],
            show_choices=False
        )
        
        selected_year = year_map[study_year_choice]
        study_year_id = selected_year.get('id')
        
        console.print(f"[bold green]Selected study year: {selected_year.get('nameEt')}[/bold green]")
        
        # Get journals for the selected study year
        console.print("[bold blue]Fetching journals...[/bold blue]")
        journal_data = get_journals(study_year_id, cookie)
        if not journal_data:
            console.print("[bold red]No journals found for the selected study year.[/bold red]")
            return
        
        # If the all-journals flag is set, process all journals
        if args.all_journals:
            console.print(f"[bold blue]Processing all {len(journal_data)} journals...[/bold blue]")
            successful_journals = 0
            for i, journal_entry in enumerate(journal_data, 1):
                # Check what we received - if it's just an ID (integer) or a dictionary
                if isinstance(journal_entry, dict) and 'id' in journal_entry:
                    journal_id = journal_entry['id']
                    journal_name = journal_entry.get('nameEt', 'Unknown')
                elif isinstance(journal_entry, (int, str)):
                    # If it's just an ID
                    journal_id = str(journal_entry)
                    journal_name = f"Journal {journal_id}"
                else:
                    console.print(f"[bold yellow]Skipping journal {i} - invalid format: {journal_entry}[/bold yellow]")
                    continue
                
                console.print(f"[bold cyan]Processing journal {i} of {len(journal_data)}: {journal_name} (ID: {journal_id})[/bold cyan]")
                
                if process_journal(journal_id, cookie):
                    successful_journals += 1
                
                console.print("\n" + "-" * 80 + "\n")
            
            console.print(f"[bold green]Successfully processed {successful_journals} out of {len(journal_data)} journals[/bold green]")
        else:
            # Display journals and prompt for selection
            journal_map = display_journals(journal_data)
            journal_choice = IntPrompt.ask(
                "Select a journal (enter the option number)", 
                choices=[str(i) for i in journal_map.keys()],
                show_choices=False
            )
            
            selected_journal = journal_map[journal_choice]
            journal_id = selected_journal.get('id')
            
            console.print(f"[bold green]Selected journal: {selected_journal.get('nameEt')}[/bold green]")
            
            # Process the selected journal
            process_journal(journal_id, cookie)

    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]HTTP Error: {e}[/bold red]")
        if e.response.status_code == 401 or e.response.status_code == 403:
            console.print("[bold yellow]Authentication failed. Your cookie may be expired or invalid.[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")

# Run the application
if __name__ == "__main__":
    main()










