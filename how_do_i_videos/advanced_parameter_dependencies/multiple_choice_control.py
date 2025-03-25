def get_options_list(field, control_value=None, control_values=[], **kwargs):
   """
   A plug-in for building a list of options for 'Plants'
   based on the values selected for the controlling field 'Plant Type'
   field: This is the dependent field.
   control_value: You won't need to use in this case, but is still required in the kwargs in the function definition.
   control_values: A list of values selected on the form for the controlling field.
   """
   options = []

   if 'Trees' in control_values:
      options.extend([
         ('red_maple', 'Red Maple'),
         ('coastal_redwood', 'Coastal Redwood'),
         ('douglas_fir', 'Douglas Fir'),
         ])

   if 'Shrubs' in control_values:
      options.extend([
         ('red_twig_dogwood', 'Red Twig Dogwood'),
         ('wild_lilac', 'Wild Lilac'),
         ('summersweet', 'Summersweet'),
      ])

   return options