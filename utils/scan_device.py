#!/usr/bin/python
## main
''' Run this program to scan the sample and detect graphene'''
from utils.lib.coordinate_creator import coordinate_generator
from utils.lib.preprocessing import check_screen_scale_rate
from utils.lib.microscope_controller import esp, prior_motor
from datetime import datetime
import os
import sys
import pandas as pd

def scan_device():
    # check if screen scale rate equal to 1.5
    check_screen_scale_rate(1)

    # [TIME] setup a start_time and record progress
    start_time = datetime.now()
    progress = 0.

    # newport controller device, baud rate, default axis
    controller = esp(dev="COM3",b=921600,axis=1,reset=True,initpos=0.0,useaxis=[],timeout=0.5)
    mt = prior_motor("COM1")

    # Get the origin x, y (input_1_x & y)
    input_1_x, input_1_y = controller.get_pos()

    # Create folder that named by current time to store photos and log file
    folder_name = str(start_time)[:19].replace(':', "'")
    DATA_PATH = f'./data/{folder_name}'
    RESULT_PATH = f'{DATA_PATH}/Detection result'
    IMG_PATH = DATA_PATH + '/Origin.png'
    os.mkdir(DATA_PATH)
    os.mkdir(RESULT_PATH)

    # Perfrom 9 times z scans to find the best figure ranging from -20 to 20
    origin_z = mt.focusLens(7, 30, IMG_PATH)

    # Write the info to a txt file
    with open(RESULT_PATH+'/Log file.txt', 'a') as f:
        f.write('Start_time: ' + str(start_time)[:-7] + '\n')
        f.write('The Origin coordinate: x = ' + str(input_1_x) + ', y = ' + str(input_1_y) + '\n')

    # generate main corrd. and extra coord. (pd.dataframe)
    main, extra, num_x, num_y = coordinate_generator(input_1_x, input_1_y)

    # get the total length of corrdinates for looping later
    row_len = main.shape[0]

    # creat z record
    z_array = []


    count_row = 1
    reverse = 1

    try:
        # Start looping every coordinate and save screenshot 
        for i in range(row_len):
            # Get the start point from corrdinate generator
            abs_x = main.iloc[i][0]
            abs_y = main.iloc[i][1]
            # apply the start point to it
            controller.x_y_move(abs_x, abs_y)

            IMG_PATH = './'+ folder_name +'/'+ str(i) + '.png'
            # return the best quality z
            if count_row % (num_y + 1) == 0:
                count_row = 1
                reverse *= -1
            abs_z = mt.focusLens_fast2(2, 5, IMG_PATH, reverse)

            print(f'{i}th figure. Clear z is: {abs_z}')
            progress += 1
            print(f'\nCurrent progress: {round(progress/row_len*100)}%')
            z_record = (abs_x, abs_y, abs_z)
            z_array.append(z_record)
            count_row += 1
    except:
        # Go back to origin x, y (input_1_x & y)
        controller.x_y_move(input_1_x, input_1_y)
        controller.close()
        # Adjust the z to the original place
        mt.move_z_pos(origin_z)
        mt.close()
        sys.exit()
        
    # [TIME] Calculate the time differnece
    end_time = datetime.now()    
    time_delta = (end_time - start_time)

    # Go back to origin x, y (input_1_x & y)
    controller.x_y_move(input_1_x, input_1_y)
    del controller

    # Adjust the z to the original place
    mt.move_z_pos(origin_z)
    del mt

    # [Time] Print time information
    print('Run finished.\nStart time: ' + str(start_time)[:-7] + '\nEnd time: ' + str(end_time)[:-7] + '\nElapsed time: ' + str(time_delta)[:-7])

    # Write info to a txt
    f = open(RESULT_PATH+'/Log file.txt', 'a')
    f.write('End_time: ' + str(end_time)[:-7] + '\n')
    f.write('Elapsed time: ' + str(time_delta)[:-7] + '\n\n')
    f.close()

    # Save the coordinates and z value
    z_data = pd.DataFrame(z_array)
    z_data.to_csv(RESULT_PATH+'/main_coordinates.txt', sep='\t', mode='w')


    # Start TF2 Object Detection
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    from utils.graphene_detection import detect
    detect(folder_name, RESULT_PATH, main, probability=0.3, flip_horizontally=False, grayscale=False)
