from datetime import datetime


class Ticket:
    def __init__(self, description: str):
        self.description = description
        self.short_description = None
        self.status = "open"
        self.category = None
        self.sub_category = None
        self.resolution_choice = None
        self.resolution_details = None
        self.raised_on = datetime.now()
        self.raised_by = None
        
    def print_ticket(self):
        return f"""
                User Query: {self.description}
                Short Description: {self.short_description}
                Status: {self.status}
                Rasied On: {self.raised_on}
                Category: {self.category}
                Sub Category: {self.sub_category}
              """
        