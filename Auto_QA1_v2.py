"""
This is an update for Auto_QA1.
It shows the outputs selected by the customer to ensure that we don’t miss anything during QA2.
"""

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import io
import os
import json 

def extract_sections(pdf_path, headers):
    doc = fitz.open(pdf_path)
    text = []
    image_list = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" in block:
                block_text = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"] + " "

                text.append(block_text)

        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            if image.width >= 500 and image.height >= 500:                   
                image_list.append(image)
    
    return text, image_list


#Define the PDF path and headers to look for
PUUID = input('PUUID: ')
statsjson = f'aws s3 --profile dh cp s3://skycatch-processing-jobs-405381464100/{PUUID}/project/stats.json .'
try:
    os.system(statsjson)
    with open('stats.json','r') as jsonderulo:
        ppkstats = json.load(jsonderulo)
        ppkfix = ppkstats['geotags']['fix']
        ppkall = ppkstats['geotags']['all']
        ppkfixrate = ppkfix/ppkall
        corrtype = f"PPK Fix Rate: {ppkfixrate*100}%"
    os.system('rm stats.json')

except:
    print("----->!!!No PPK Stats, could be RTK or standard GPS!!!<-----")
    corrtype = "RTK-Corrected or Standard GPS (No Correction)"
    ppkfix = "No PPK Geotags"
    ppkall = "No PPK Geotags"

# Download and parse outputs.json
outputs_json = f'aws s3 --profile dh cp s3://skycatch-processing-jobs-405381464100/{PUUID}/outputs.json .'
os.system(outputs_json)

selected_outputs = []
try:
    with open('outputs.json', 'r') as json_file:
        outputs = json.load(json_file)

    # Generic keyword-based selection
    if outputs.get("custom_basemap.skybasemap", 0):
        selected_outputs.append("custom basemap")

    if any("mesh" in key and outputs.get(key, 0) for key in outputs):
        selected_outputs.append("3D mesh")

    if any("dsm" in key and outputs.get(key, 0) for key in outputs):
        selected_outputs.append("DSM")

    if any("dtm" in key and outputs.get(key, 0) for key in outputs):
        selected_outputs.append("DTM")

    if any("ground" in key and outputs.get(key, 0) for key in outputs):
        selected_outputs.append("ground return")

    if any("removed" in key and outputs.get(key, 0) for key in outputs):
        selected_outputs.append("removed objects")

    if any("sub" in key and outputs.get(key, 0) for key in outputs):
        selected_outputs.append("subsampled outputs")

    if outputs.get("terrain_following.geotiff", 0):
        selected_outputs.append("terrain following")

except Exception as e:
    print("Error retrieving outputs:", e)
    selected_outputs.append("Error retrieving outputs")


try:
    sync = f'aws s3 --profile dh cp s3://skycatch-processing-jobs-405381464100/{PUUID}/project/backup/1_initial/report/project_report.pdf .'
    os.system(sync)
    pdf_path = "project_report.pdf"
    headers = ["Summary"]  # Add your section headers here
    text, images = extract_sections(pdf_path, headers)


    text_file = f"VISOPs_Summary.txt"    
    with open(text_file, "w", encoding="utf-8") as f:
        for content in text:
            f.write(f"{content}\n")


    total_width = max(image.width for image in images)
    total_height = sum(image.height for image in images)
    combined_image = Image.new('RGB', (total_width, total_height))
    y_offset = 0
    for image in images:
        combined_image.paste(image, (0, y_offset))
        y_offset += image.height
    combined_image.save(f"flight.png")

    #for page_num, img_index, image in images:
        #image.save(f"image_page_{page_num}_img_{img_index}.png")

    with open(text_file, "r", encoding="utf-8") as file:
        keywords = ['Camera Model Name(s)', 'Average Ground Sampling Distance (GSD)',
                    'Number of Calibrated Images', 'Number of Geolocated Images', 'Ground Control Points',
                    'Absolute Geolocation Variance', 'Sigma [m]', 'RMS Error [m]']
        lines = file.readlines()
        with open(text_file, "w", encoding="utf-8") as summarize:
            # Function to group remaining outputs into two balanced lines
            def balance_remaining_outputs(remaining_outputs, max_line_length=40):
                """
                Groups remaining outputs into two balanced lines.
                :param remaining_outputs: List of output strings after the first line.
                :param max_line_length: Maximum character count per line (default: 40).
                :return: Two balanced lines as strings.
                """
                line1 = []
                line2 = []
                length1 = 0
                length2 = 0

                for output in remaining_outputs:
                    # Try adding the output to the first line
                    if length1 + len(output) + (2 if line1 else 0) <= max_line_length:
                        line1.append(output)
                        length1 += len(output) + (2 if line1 else 0)
                    # Otherwise, add it to the second line
                    elif length2 + len(output) + (2 if line2 else 0) <= max_line_length:
                        line2.append(output)
                        length2 += len(output) + (2 if line2 else 0)
                    # If neither line has space, prioritize the second line
                    else:
                        line2.append(output)
                        length2 += len(output) + (2 if line2 else 0)

                return ", ".join(line1), ", ".join(line2)


            # Split selected_outputs into three lines: First line with 2 items, then balance the rest
            first_line = ", ".join(selected_outputs[:2])  # First line with 2 items
            remaining_outputs = selected_outputs[2:]  # Remaining items after the first line

            # Balance the remaining outputs into two lines
            second_line, third_line = balance_remaining_outputs(remaining_outputs)

            # Add a comma to the first line only if there is a second line
            if second_line.strip():  # Check if the second line is not empty
                first_line_with_comma = first_line + ","  # Add a comma to the first line
            else:
                first_line_with_comma = first_line  # No comma if there is no second line

            # Add a comma to the second line only if there is a third line
            if third_line.strip():  # Check if the third line is not empty
                second_line_with_comma = second_line + ","  # Add a comma to the second line
            else:
                second_line_with_comma = second_line  # No comma if there is no third line

            # Combine the lines with proper indentation
            formatted_outputs = (
                first_line_with_comma + "\n" +
                "                 " + second_line_with_comma + "\n" +
                "                 " + third_line  # No comma for the third line
            )

            summarize.write(
                f'------------------------------------------------------------------------------------------\n'
                f'------------------------------------------------------------------------------------------\n'
                f'---------------------------------------------------PROCESSING JOB SUMMARY---------------------------------------------------\n'
                f'--------------------------------------------{PUUID}--------------------------------------------\n'
                f'------------------------------------------------------------------------------------------\n'
                f'------------------------------------------------------------------------------------------\n'
                f'PPK Fix Status = {ppkfix}\n'
                f'Images Geotagged = {ppkall}\n'
                f'{corrtype}\n'
                f'Outputs Selected: {formatted_outputs}\n'  # Outputs are now split into three lines
                f'------------------------------------------------------------------------------------------\n'
                f'------------------------------------------------------------------------------------------\n'
            )
            print('--------------------------------------------------------')
            print('--------------------------------------------------------')
            print("-----------------PROCESSING JOB SUMMARY-----------------")
            print(f"----------{PUUID}----------")
            print('--------------------------------------------------------')
            print('--------------------------------------------------------')
            print("PPK Fix Status = ", ppkfix)
            print("Images Geotagged = ", ppkall)
            print(corrtype)
            print(f"Outputs Selected: {', '.join(selected_outputs)}")
            print('--------------------------------------------------------')
            for i in lines:
                if any(keyword in i for keyword in keywords):
                    print(i)
                    summarize.write(i)
            summarize.write(f'------------------------------------------------------------------------------------------\n------------------------------------------------------------------------------------------\n')
            print('-------------------------------------------------------')
            print('-------------------------------------------------------')

except:
    print("----->!!!Error Encountered Reading Project Report!!!<-----")
    print("------>!!! Please do manual QA1 in the meantime !!!<------")

# FINAL_IMAGE_CREATOR
try:
    flight_image = Image.open('flight.png')
    logo_image = Image.open('Logo.png')

    with open('VISOPs_Summary.txt', 'r') as file:
        text = file.read()

    font_size = 18
    font = ImageFont.truetype("cour.ttf", font_size)  # Make sure to have a TTF font file

    max_text_width = flight_image.width
    lines = text.split('\n')  # Split text into lines
    text_height = len(lines) * font_size  # Calculate total height based on number of lines

    logo_width, logo_height = logo_image.size
    logo_x = (max_text_width - logo_width) // 2
    logo_y = 20  # Adjust as needed for vertical positioning

    new_height = logo_y + logo_height + text_height + flight_image.height
    new_image = Image.new('RGB', (max_text_width, new_height), color='white')
    draw = ImageDraw.Draw(new_image)

    text_color = (0, 0, 0)  # Black
    background_color = (192, 192, 192)  # Grey color (adjust as needed)

    draw.rectangle([0, 0, max_text_width, logo_y + logo_height + text_height], fill=background_color)
    new_image.paste(logo_image, (logo_x, logo_y))

    draw_new = ImageDraw.Draw(new_image)
    y = logo_y + logo_height

    for line in lines:
        text_width = draw_new.textlength(line, font=font)  # Get text width
        x = (max_text_width - text_width) // 2  # Calculate x position to center text
        draw_new.text((x, y), line, font=font, fill=text_color)
        y += font_size  # Move to the next line

    # Paste original image onto the new image
    new_image.paste(flight_image, (0, logo_y + logo_height + text_height))

    # Save the result
    new_image.save('PJ_Receipt.png')
    os.remove('flight.png')
except Exception as e:
    print("----->!!!Error Encountered Reading Project Report!!!<-----")
    print(f"Error: {e}")
